from flask import abort

ALLOWED_CATEGORIES = [
    "Food", "Travel", "Shopping", "Bills", "Rent", "Entertainment",
    "Health", "Groceries", "Education", "Other"
]


def validate_category(category: str):
    if category not in ALLOWED_CATEGORIES:
        abort(400, description=f"Invalid category. Allowed: {', '.join(ALLOWED_CATEGORIES)}")


def validate_amount(amount):
    try:
        value = float(amount)
        if value <= 0:
            raise ValueError
        return value
    except Exception:
        abort(400, description="Amount must be a positive number")
