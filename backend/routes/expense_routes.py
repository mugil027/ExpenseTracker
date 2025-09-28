from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from typing import Union
from models.expense_model import (
    add_expense, get_expenses, delete_expense, update_expense,
    agg_summary_by_category, agg_spend_over_time
)
from utils.validation import validate_category, validate_amount, ALLOWED_CATEGORIES

expense_bp = Blueprint("expenses", __name__)


@expense_bp.get("/categories")
def list_categories():
    return jsonify({"categories": ALLOWED_CATEGORIES})


@expense_bp.post("/expenses")
@jwt_required()
def create_expense():
    user_id = get_jwt_identity()
    data = request.get_json(force=True)

    category = data.get("category")
    amount = data.get("amount")
    note = data.get("note")

    validate_category(category)
    amount = validate_amount(amount)

    add_expense(user_id, category, amount, note)
    return jsonify({"msg": "Expense added"}), 201


@expense_bp.get("/expenses")
@jwt_required()
def list_expenses():
    user_id = get_jwt_identity()
    # Optional ISO date filters: ?start=2025-08-01&end=2025-08-31
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
    ])


@expense_bp.delete("/expenses/<expense_id>")
@jwt_required()
def remove_expense(expense_id):
    user_id = get_jwt_identity()
    res = delete_expense(user_id, expense_id)
    if res.deleted_count == 0:
        return jsonify({"msg": "Not found"}), 404
    return jsonify({"msg": "Deleted"}), 200


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

    res = update_expense(user_id, expense_id, updates)
    if res.matched_count == 0:
        return jsonify({"msg": "Not found"}), 404
    return jsonify({"msg": "Updated"}), 200


@expense_bp.get("/expenses/summary")
@jwt_required()
def summary_by_category():
    user_id = get_jwt_identity()
    start = request.args.get("start")
    end = request.args.get("end")
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    data = agg_summary_by_category(user_id, start_dt, end_dt)
    return jsonify(data)


@expense_bp.get("/expenses/series")
@jwt_required()
def spend_over_time():
    user_id = get_jwt_identity()
    period = request.args.get("period", "month")  # day|week|month
    data = agg_spend_over_time(user_id, period)
    return jsonify(data)
