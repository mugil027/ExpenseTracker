# routes/investment_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import mongo
from datetime import datetime, timedelta
from pathlib import Path
import json
import math
from nsetools import Nse
import yfinance as yf
import pandas as pd

investment_bp = Blueprint("investment", __name__)

# ---------- Helpers ----------

def _to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(',', '').strip())
    except Exception:
        return None


# Built-in short list (fallback if no JSON provided)
_BUILTIN_LIST = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services"},
    {"symbol": "INFY.NS", "name": "Infosys"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank"},
    {"symbol": "SBIN.NS", "name": "State Bank of India"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance"},
    {"symbol": "ITC.NS", "name": "ITC"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank"},
    {"symbol": "TITAN.NS", "name": "Titan"},
]

def _load_symbol_list():
    """Load NSE symbols from ./data/nse_symbols.json if present; else fallback."""
    p = Path(__file__).resolve().parent.parent / "data" / "nse_symbols.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            # normalize shape
            out = []
            for row in data:
                sym = row.get("symbol") or row.get("Symbol")
                name = row.get("name") or row.get("Name") or row.get("Company Name") or sym
                if sym:
                    out.append({"symbol": sym, "name": name})
            if out:
                return out
        except Exception:
            pass
    return _BUILTIN_LIST

def _status_from(change):
    if change > 0: return "up"
    if change < 0: return "down"
    return "flat"

nse = Nse()

def _intraday_quote(symbol: str):
    # Try NSE first (without .NS suffix)
    try:
        if symbol.endswith(".NS"):
            base_symbol = symbol.replace(".NS", "")
        else:
            base_symbol = symbol

        q = nse.get_quote(base_symbol)
        if q:
            price = q.get("lastPrice")
            prev = q.get("previousClose")
            if price is not None and prev is not None:
                change = price - prev
                return {
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "status": "up" if change > 0 else ("down" if change < 0 else "flat")
                }
    except Exception as e:
        print(f"NSE fetch failed for {symbol}: {e}")

    # Fallback to yfinance if NSE fails
    import yfinance as yf
    t = yf.Ticker(symbol)
    try:
        hist = t.history(period="1d")
        if hist is None or hist.empty:
            if symbol.endswith(".NS"):
                alt = symbol.replace(".NS", ".BO")
                t = yf.Ticker(alt)
                hist = t.history(period="1d")
                symbol = alt
        if hist is None or hist.empty:
            return None
        last = float(hist["Close"].iloc[-1])
        opn = float(hist["Open"].iloc[0])
        chg = last - opn
        return {"symbol": symbol, "price": round(last, 2), "change": round(chg, 2), "status": _status_from(chg)}
    except Exception as e:
        print(f"yfinance failed for {symbol}: {e}")
        return None
def _history(symbol: str, range_key: str, interval: str):
    """
    Get history points for Chart.js.
    range_key in {"1d","1w","1mo"}; interval auto-mapped for quality.
    """
    t = yf.Ticker(symbol)
    if range_key == "1d":
        hist = t.history(period="1d", interval="5m")
    elif range_key == "1w":
        hist = t.history(period="5d", interval="30m")
    else:  # default 1mo
        hist = t.history(period="1mo", interval="1d")

    if hist is None or hist.empty:
        return []

    points = []
    for ts, row in hist.iterrows():
        points.append({
            "t": ts.to_pydatetime().isoformat(),
            "o": float(row["Open"]),
            "h": float(row["High"]),
            "l": float(row["Low"]),
            "c": float(row["Close"])
        })

    return points

# ---------- Autocomplete search ----------

@investment_bp.get("/api/invest/search")
@jwt_required()
def search_stocks():
    q = (request.args.get("q") or "").lower().strip()
    if not q:
        return jsonify([])
    listing = _load_symbol_list()
    results = [s for s in listing if q in s["name"].lower() or q in s["symbol"].lower()]
    return jsonify(results[:20])

# ---------- Quote & History ----------

@investment_bp.get("/api/invest/quote/<symbol>")
@jwt_required()
def get_quote(symbol):
    try:
        q = _intraday_quote(symbol)
        if not q or not isinstance(q, dict) or "price" not in q:
            # Always return valid JSON so frontend never crashes
            return jsonify({
                "symbol": symbol,
                "price": None,
                "change": 0,
                "status": "flat",
                "error": f"no_data_for_{symbol}"
            }), 200
        return jsonify(q), 200
    except Exception as e:
        print(f"Quote error for {symbol}: {e}")
        return jsonify({
            "symbol": symbol,
            "price": None,
            "change": 0,
            "status": "flat",
            "error": str(e)
        }), 200


@investment_bp.get("/api/invest/history/<symbol>")
@jwt_required()
def get_history(symbol):
    range_key = request.args.get("range", "1mo")
    interval = request.args.get("interval", "")  # ignored; we auto map above
    pts = _history(symbol, range_key, interval)
    return jsonify({"points": pts})

# ---------- Watchlist (per user) ----------

@investment_bp.get("/api/invest/watchlist")
@jwt_required()
def get_watchlist():
    user_id = get_jwt_identity()
    doc = mongo.db.watchlists.find_one({"user_id": user_id})
    return jsonify(doc.get("items", []) if doc else [])

@investment_bp.post("/api/invest/watchlist")
@jwt_required()
def add_watchlist():
    user_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    symbol = (body.get("symbol") or "").strip()
    name = (body.get("name") or "").strip() or symbol
    if not symbol:
        return jsonify({"msg": "symbol required"}), 400
    mongo.db.watchlists.update_one(
        {"user_id": user_id},
        {
            "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()},
            "$addToSet": {"items": {"symbol": symbol, "name": name}},
        },
        upsert=True,
    )
    return jsonify({"msg": "added"}), 201

@investment_bp.delete("/api/invest/watchlist/<symbol>")
@jwt_required()
def remove_watchlist(symbol):
    user_id = get_jwt_identity()
    res = mongo.db.watchlists.update_one(
        {"user_id": user_id},
        {"$pull": {"items": {"symbol": symbol}}},
    )
    if res.modified_count == 0:
        return jsonify({"msg": "not_found"}), 404
    return jsonify({"msg": "removed"}), 200

@investment_bp.get("/api/invest/watchlist/quotes")
@jwt_required()
def watchlist_quotes():
    user_id = get_jwt_identity()
    doc = mongo.db.watchlists.find_one({"user_id": user_id}) or {"items": []}
    out = []
    for it in doc.get("items", []):
        q = _intraday_quote(it["symbol"])
        if q:
            q["name"] = it.get("name", it["symbol"])
            out.append(q)
    return jsonify(out)

# ---------- Portfolio positions (qty, avg_price) ----------

# One doc per user_id; items: [{symbol, name, qty, avg_price}]
@investment_bp.get("/api/invest/positions")
@jwt_required()
def get_positions():
    user_id = get_jwt_identity()
    doc = mongo.db.positions.find_one({"user_id": user_id})
    return jsonify(doc.get("items", []) if doc else [])

@investment_bp.post("/api/invest/positions")
@jwt_required()
def upsert_position():
    user_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    symbol = (body.get("symbol") or "").strip()
    name = (body.get("name") or "").strip() or symbol
    qty = float(body.get("qty", 0))
    avg_price = float(body.get("avg_price", 0))
    if not symbol or qty <= 0 or avg_price <= 0:
        return jsonify({"msg": "symbol, qty>0 & avg_price>0 required"}), 400

    # Update if exists, else append
    mongo.db.positions.update_one(
        {"user_id": user_id, "items.symbol": symbol},
        {"$set": {"items.$.qty": qty, "items.$.avg_price": avg_price, "items.$.name": name}},
        upsert=False,
    )
    # If not modified, push new
    if not mongo.db.positions.find_one({"user_id": user_id, "items.symbol": symbol}):
        mongo.db.positions.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()},
                "$push": {"items": {"symbol": symbol, "name": name, "qty": qty, "avg_price": avg_price}},
            },
            upsert=True,
        )
    return jsonify({"msg": "upserted"}), 200

@investment_bp.delete("/api/invest/positions/<symbol>")
@jwt_required()
def delete_position(symbol):
    user_id = get_jwt_identity()
    res = mongo.db.positions.update_one(
        {"user_id": user_id},
        {"$pull": {"items": {"symbol": symbol}}},
    )
    if res.modified_count == 0:
        return jsonify({"msg": "not_found"}), 404
    return jsonify({"msg": "removed"}), 200

@investment_bp.get("/api/invest/portfolio/summary")
@jwt_required()
def portfolio_summary():
    """
    Returns per-position P&L and overall aggregates:
    { positions: [{symbol,name,qty,avg_price,ltp,mtm,invested,value,pl,pl_pct,status}], totals: {...} }
    """
    user_id = get_jwt_identity()
    doc = mongo.db.positions.find_one({"user_id": user_id}) or {"items": []}
    items = doc.get("items", [])

    positions = []
    total_invested = 0.0
    total_value = 0.0

    for it in items:
        symbol = it["symbol"]
        name = it.get("name", symbol)
        qty = float(it.get("qty", 0))
        avg_price = float(it.get("avg_price", 0))
        if qty <= 0 or avg_price <= 0:
            continue

        q = _intraday_quote(symbol) or {"price": 0, "change": 0, "status": "flat"}
        ltp = float(q["price"])
        invested = qty * avg_price
        value = qty * ltp
        pl = value - invested
        pl_pct = (pl / invested * 100.0) if invested > 0 else 0.0

        positions.append({
            "symbol": symbol, "name": name, "qty": qty, "avg_price": round(avg_price, 2),
            "ltp": round(ltp, 2), "invested": round(invested, 2), "value": round(value, 2),
            "pl": round(pl, 2), "pl_pct": round(pl_pct, 2), "status": q["status"]
        })
        total_invested += invested
        total_value += value

    totals = {
        "invested": round(total_invested, 2),
        "value": round(total_value, 2),
        "pl": round(total_value - total_invested, 2),
        "pl_pct": round(((total_value - total_invested) / total_invested * 100.0), 2) if total_invested > 0 else 0.0
    }

    return jsonify({"positions": positions, "totals": totals})
