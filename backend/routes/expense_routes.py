from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from typing import Union
from bson import ObjectId
from database import mongo
from models.expense_model import (
    add_expense, get_expenses, delete_expense, update_expense,
    agg_summary_by_category, agg_spend_over_time
)
from utils.validation import validate_category, validate_amount, ALLOWED_CATEGORIES

expense_bp = Blueprint("expenses", __name__)

# --- Helper to parse ISO dates safely ---
def _parse_utc(dt_str: str):
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


# ✅ List allowed categories
@expense_bp.get("/categories")
def list_categories():
    return jsonify({"categories": ALLOWED_CATEGORIES})


# ✅ Add new expense
@expense_bp.post("/expenses")
@jwt_required()
def create_expense():
    user_id = get_jwt_identity()
    data = request.get_json(force=True)

    category = data.get("category")
    amount = data.get("amount")
    note = data.get("note")
    date = data.get("date")  # ← optional custom date (ISO format)

    validate_category(category)
    amount = validate_amount(amount)

    add_expense(user_id, category, amount, note, date)
    return jsonify({"msg": "Expense added"}), 201


# ✅ Fetch all expenses (optional filters)
@expense_bp.get("/expenses")
@jwt_required()
def list_expenses():
    user_id = get_jwt_identity()
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    def parse(dt: Union[str, None]):
        return datetime.fromisoformat(dt).astimezone(timezone.utc) if dt else None

    items = get_expenses(user_id, parse(start_str), parse(end_str))
    return jsonify([
        {
            "id": str(x["_id"]),
            "category": x["category"],
            "amount": x["amount"],
            "note": x.get("note", ""),
            "created_at": x["created_at"].isoformat()
        }
        for x in items
    ]), 200


# ✅ Delete expense
@expense_bp.delete("/expenses/<expense_id>")
@jwt_required()
def remove_expense(expense_id):
    user_id = get_jwt_identity()
    res = mongo.db.expenses.delete_one({
        "_id": ObjectId(expense_id),
        "user_id": str(user_id)
    })
    if res.deleted_count == 0:
        return jsonify({"msg": "Not found"}), 404
    return jsonify({"msg": "Deleted"}), 200


# ✅ Update expense
@expense_bp.patch("/expenses/<expense_id>")
@jwt_required()
def patch_expense(expense_id):
    user_id = get_jwt_identity()
    data = request.get_json(force=True)

    updates = {}
    if "category" in data:
        validate_category(data["category"])
        updates["category"] = data["category"]
    if "amount" in data:
        updates["amount"] = validate_amount(data["amount"])
    if "note" in data:
        updates["note"] = data.get("note") or ""

    res = mongo.db.expenses.update_one(
        {"_id": ObjectId(expense_id), "user_id": str(user_id)},
        {"$set": updates}
    )
    if res.matched_count == 0:
        return jsonify({"msg": "Not found"}), 404
    return jsonify({"msg": "Updated"}), 200


# ✅ Summary by category
@expense_bp.get("/expenses/summary")
@jwt_required()
def summary_by_category():
    user_id = get_jwt_identity()
    start = request.args.get("start")
    end = request.args.get("end")
    start_dt = _parse_utc(start)
    end_dt = _parse_utc(end)

    data = agg_summary_by_category(user_id, start_dt, end_dt)
    return jsonify(data), 200


# ✅ Spend over time
@expense_bp.get("/expenses/series")
@jwt_required()
def spend_over_time():
    user_id = get_jwt_identity()
    period = request.args.get("period", "month")  # day|week|month
    data = agg_spend_over_time(user_id, period)
    return jsonify(data), 200
