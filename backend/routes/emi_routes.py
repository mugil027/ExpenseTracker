# routes/emi_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import mongo
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from email.utils import parseaddr
from routes.notification_routes import send_email  # reuse SMTP sender

emi_bp = Blueprint("emi_bp", __name__)

# ---------- Helpers ----------
def _parse_iso(dt_str):
    return datetime.fromisoformat(dt_str).astimezone(timezone.utc)

def _as_dict(doc):
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "description": doc.get("description", ""),
        "amount": float(doc["amount"]),
        "due_date": doc["due_date"].isoformat(),
        "created_at": doc["created_at"].isoformat(),
        "status": doc.get("status", "pending")
    }

def _as_loan_dict(doc):
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "description": doc.get("description", ""),
        "principal": float(doc["principal"]),
        "interest_rate": float(doc["interest_rate"]),
        "start_date": doc["start_date"].isoformat(),
        "tenure_months": int(doc["tenure_months"]),
        "emi_amount": float(doc["emi_amount"]),
        "created_at": doc["created_at"].isoformat()
    }

def _calc_emi(principal, annual_rate_percent, n_months):
    r = (annual_rate_percent / 100.0) / 12.0
    if r == 0:
        return round(principal / max(n_months, 1), 2)
    num = principal * r * ((1 + r) ** n_months)
    den = ((1 + r) ** n_months) - 1
    return round(num / den, 2)

# ---------- EMI CRUD ----------
@emi_bp.post("/api/emis")
@jwt_required()
def create_emi():
    user_id = get_jwt_identity()
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    amount = float(data.get("amount", 0))
    due_date = data.get("due_date")
    description = (data.get("description") or "").strip()
    if not title or amount <= 0 or not due_date:
        return jsonify({"msg": "title, amount>0, due_date required"}), 400

    doc = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "amount": amount,
        "due_date": _parse_iso(due_date),
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }
    ins = mongo.db.emis.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return jsonify(_as_dict(doc)), 201

@emi_bp.get("/api/emis")
@jwt_required()
def list_emis():
    user_id = get_jwt_identity()
    cur = mongo.db.emis.find({"user_id": user_id}).sort("due_date", 1)
    return jsonify([_as_dict(x) for x in cur])

@emi_bp.patch("/api/emis/<emi_id>")
@jwt_required()
def update_emi(emi_id):
    user_id = get_jwt_identity()
    payload = request.get_json(force=True) or {}
    updates = {}
    for k in ("title", "description", "status"):
        if k in payload: updates[k] = payload[k]
    if "amount" in payload:
        updates["amount"] = float(payload["amount"])
    if "due_date" in payload:
        updates["due_date"] = _parse_iso(payload["due_date"])

    res = mongo.db.emis.update_one(
        {"_id": ObjectId(emi_id), "user_id": user_id},
        {"$set": updates}
    )
    if res.matched_count == 0:
        return jsonify({"msg": "not_found"}), 404
    doc = mongo.db.emis.find_one({"_id": ObjectId(emi_id)})
    return jsonify(_as_dict(doc)), 200

@emi_bp.delete("/api/emis/<emi_id>")
@jwt_required()
def delete_emi(emi_id):
    user_id = get_jwt_identity()
    res = mongo.db.emis.delete_one({"_id": ObjectId(emi_id), "user_id": user_id})
    if res.deleted_count == 0:
        return jsonify({"msg": "not_found"}), 404
    return jsonify({"msg": "deleted"}), 200

# ---------- Loans CRUD ----------
@emi_bp.post("/api/loans")
@jwt_required()
def create_loan():
    user_id = get_jwt_identity()
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    principal = float(data.get("principal", 0))
    rate = float(data.get("interest_rate", 0))
    tenure = int(data.get("tenure_months", 0))
    start_date = data.get("start_date")

    if not title or principal <= 0 or rate < 0 or tenure <= 0 or not start_date:
        return jsonify({"msg": "title, principal>0, interest_rate>=0, tenure>0, start_date required"}), 400

    emi_amt = _calc_emi(principal, rate, tenure)
    doc = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "principal": principal,
        "interest_rate": rate,
        "tenure_months": tenure,
        "start_date": _parse_iso(start_date),
        "emi_amount": emi_amt,
        "created_at": datetime.now(timezone.utc)
    }
    ins = mongo.db.loans.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return jsonify(_as_loan_dict(doc)), 201

@emi_bp.get("/api/loans")
@jwt_required()
def list_loans():
    user_id = get_jwt_identity()
    cur = mongo.db.loans.find({"user_id": user_id}).sort("created_at", -1)
    return jsonify([_as_loan_dict(x) for x in cur])

@emi_bp.patch("/api/loans/<loan_id>")
@jwt_required()
def update_loan(loan_id):
    user_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    updates = {}
    for k in ("title", "description", "interest_rate", "tenure_months"):
        if k in body: updates[k] = body[k]
    for numk in ("principal", "interest_rate"):
        if numk in updates: updates[numk] = float(updates[numk])
    if "tenure_months" in updates: updates["tenure_months"] = int(updates["tenure_months"])
    if "start_date" in body: updates["start_date"] = _parse_iso(body["start_date"])

    # If anything affecting EMI changed, recompute
    doc = mongo.db.loans.find_one({"_id": ObjectId(loan_id), "user_id": user_id})
    if not doc: return jsonify({"msg": "not_found"}), 404
    principal = float(updates.get("principal", doc["principal"]))
    rate = float(updates.get("interest_rate", doc["interest_rate"]))
    tenure = int(updates.get("tenure_months", doc["tenure_months"]))
    updates["emi_amount"] = _calc_emi(principal, rate, tenure)

    res = mongo.db.loans.update_one({"_id": ObjectId(loan_id), "user_id": user_id}, {"$set": updates})
    doc = mongo.db.loans.find_one({"_id": ObjectId(loan_id)})
    return jsonify(_as_loan_dict(doc)), 200

@emi_bp.delete("/api/loans/<loan_id>")
@jwt_required()
def delete_loan(loan_id):
    user_id = get_jwt_identity()
    res = mongo.db.loans.delete_one({"_id": ObjectId(loan_id), "user_id": user_id})
    if res.deleted_count == 0:
        return jsonify({"msg": "not_found"}), 404
    return jsonify({"msg": "deleted"}), 200

# ---------- Due Soon (for popups) ----------
@emi_bp.get("/api/emis/due_soon")
@jwt_required()
def due_soon():
    user_id = get_jwt_identity()
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=3)
    cur = mongo.db.emis.find({
        "user_id": user_id,
        "due_date": {"$gte": now, "$lte": end},
        "status": {"$ne": "paid"}
    }).sort("due_date", 1)
    return jsonify([_as_dict(x) for x in cur])

# ---------- Daily email notifications (manual trigger endpoint) ----------
@emi_bp.post("/api/emis/send_due_emails")
@jwt_required()
def send_due_emails():
    """
    Call from a daily job. Body: { "email": "user@example.com" }
    Sends emails for EMIs due in exactly 3 days.
    """
    user_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    to_email = (body.get("email") or "").strip()
    if not parseaddr(to_email)[1]:
        return jsonify({"msg": "valid email required"}), 400

    start = datetime.now(timezone.utc) + timedelta(days=3)
    end = start + timedelta(days=1)
    items = list(mongo.db.emis.find({
        "user_id": user_id,
        "due_date": {"$gte": start, "$lt": end},
        "status": {"$ne": "paid"}
    }))
    for it in items:
        title = it["title"]
        amt = it["amount"]
        dt = it["due_date"].astimezone(timezone.utc).date().isoformat()
        subject = f"EMI Reminder: {title} due on {dt}"
        body = f"Hey! Your {title} of ₹{amt:.2f} is due on {dt}. Don’t forget to pay on time!"
        try:
            send_email(to_email, subject, body)
        except Exception as e:
            print("Email send failed:", e)

    return jsonify({"sent": len(items)}), 200
