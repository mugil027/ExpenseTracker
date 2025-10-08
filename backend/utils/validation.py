from flask import abort

ALLOWED_CATEGORIES = {
    "Food","Travel","Shopping","Bills","Rent","Entertainment",
    "Health","Groceries","Education","Other","Income","Investments","Savings"
}

def validate_category(cat: str):
    if not cat or cat not in ALLOWED_CATEGORIES:
        raise ValueError("invalid category")

def validate_amount(val):
    try:
        x = float(val)
        if x <= 0:
            raise ValueError()
        return x
    except Exception:
        raise ValueError("invalid amount")



        
