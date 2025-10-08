from database import mongo
from datetime import datetime, timezone
from bson import ObjectId
from typing import Union


def add_expense(user_id: str, category: str, amount: float, note: Union[str, None] = None, date: Union[str, None] = None):
    """
    Add a new expense. Handles both with-date and without-date cases safely.
    Accepts date in formats like:
    - '2025-10-07' (from <input type="date">)
    - '2025-10-07T00:00:00Z' (ISO string)
    """

    created_at = None
    if date:
        try:
            # ✅ Try full ISO format (e.g., '2025-10-07T00:00:00Z')
            created_at = datetime.fromisoformat(date.replace("Z", "+00:00"))
        except Exception:
            try:
                # ✅ Fallback for 'YYYY-MM-DD' (from date input)
                created_at = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                # ✅ Last resort
                created_at = datetime.now(timezone.utc)
    else:
        created_at = datetime.now(timezone.utc)

    doc = {
        "user_id": str(user_id),  # ✅ always store as string
        "category": category,
        "amount": float(amount),
        "note": note or "",
        "created_at": created_at,
    }

    return mongo.db.expenses.insert_one(doc)



def get_expenses(user_id: str, start: Union[datetime, None] = None, end: Union[datetime, None] = None):
    """
    Fetch expenses for the given user, optionally filtered by date range.
    """
    query = {"user_id": str(user_id)}  # ✅ match by string
    if start or end:
        query["created_at"] = {}
        if start:
            query["created_at"]["$gte"] = start
        if end:
            query["created_at"]["$lte"] = end

    cursor = mongo.db.expenses.find(query).sort("created_at", -1)
    return list(cursor)


def delete_expense(user_id: str, expense_id: str):
    """
    Delete a specific expense by its ID for a user.
    """
    return mongo.db.expenses.delete_one({
        "_id": ObjectId(expense_id),
        "user_id": str(user_id)  # ✅ ensure consistent type
    })


def update_expense(user_id: str, expense_id: str, updates: dict):
    """
    Update fields (category, amount, note) for an expense.
    """
    updates = {k: v for k, v in updates.items() if v is not None}
    return mongo.db.expenses.update_one(
        {"_id": ObjectId(expense_id), "user_id": str(user_id)},  # ✅ consistent user_id type
        {"$set": updates}
    )


def agg_summary_by_category(user_id: str, start=None, end=None):
    """
    Aggregate total spending by category for the user.
    """
    match = {"user_id": str(user_id)}
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
    """
    Aggregate total spending over time (by day, week, or month).
    """
    if period not in {"day", "week", "month"}:
        period = "month"

    date_fmt = {
        "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
        "week": {"$dateToString": {"format": "%G-W%V", "date": "$created_at"}},
        "month": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
    }[period]

    pipeline = [
        {"$match": {"user_id": str(user_id)}},  # ✅ consistent
        {"$group": {"_id": date_fmt, "total": {"$sum": "$amount"}}},
        {"$project": {"_id": 0, "period": "$_id", "total": 1}},
        {"$sort": {"period": 1}}
    ]
    return list(mongo.db.expenses.aggregate(pipeline))
