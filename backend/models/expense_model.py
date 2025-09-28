from database import mongo
from datetime import datetime, timezone
from bson import ObjectId
from typing import Union


def add_expense(user_id: str, category: str, amount: float, note: Union[str, None] = None):
    doc = {
        "user_id": ObjectId(user_id),
        "category": category,
        "amount": float(amount),
        "note": note or "",
        "created_at": datetime.now(timezone.utc)
    }
    return mongo.db.expenses.insert_one(doc)


def get_expenses(user_id: str, start: Union[datetime, None] = None, end: Union[datetime, None] = None):
    query = {"user_id": ObjectId(user_id)}
    if start or end:
        query["created_at"] = {}
        if start:
            query["created_at"]["$gte"] = start
        if end:
            query["created_at"]["$lte"] = end
    cursor = mongo.db.expenses.find(query).sort("created_at", -1)
    return list(cursor)


def delete_expense(user_id: str, expense_id: str):
    return mongo.db.expenses.delete_one({
        "_id": ObjectId(expense_id),
        "user_id": ObjectId(user_id)
    })


def update_expense(user_id: str, expense_id: str, updates: dict):
    updates = {k: v for k, v in updates.items() if v is not None}
    return mongo.db.expenses.update_one(
        {"_id": ObjectId(expense_id), "user_id": ObjectId(user_id)},
        {"$set": updates}
    )


def agg_summary_by_category(user_id: str, start=None, end=None):
    match = {"user_id": ObjectId(user_id)}
    if start or end:
        match["created_at"] = {}
        if start:
            match["created_at"]["$gte"] = start
        if end:
            match["created_at"]["$lte"] = end

    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$project": {"_id": 0, "category": "$_id", "total": 1}},
        {"$sort": {"total": -1}}
    ]
    return list(mongo.db.expenses.aggregate(pipeline))


def agg_spend_over_time(user_id: str, period: str = "month"):
    # period can be 'day', 'week', 'month'
    if period not in {"day", "week", "month"}:
        period = "month"

    date_fmt = {
        "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
        "week": {"$dateToString": {"format": "%G-W%V", "date": "$created_at"}},
        "month": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
    }[period]

    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$group": {"_id": date_fmt, "total": {"$sum": "$amount"}}},
        {"$project": {"_id": 0, "period": "$_id", "total": 1}},
        {"$sort": {"period": 1}}
    ]
    return list(mongo.db.expenses.aggregate(pipeline))
