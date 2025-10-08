# database.py
from flask_pymongo import PyMongo

mongo = PyMongo()

def init_db(app):
    mongo.init_app(app)
    with app.app_context():
        users = mongo.db.users
        expenses = mongo.db.expenses
        finance = mongo.db.finance
        # NEW
        watchlists = mongo.db.watchlists
        positions = mongo.db.positions
        emis = mongo.db.emis
        loans = mongo.db.loans

        users.create_index("username", unique=True)
        expenses.create_index([("user_id", 1), ("created_at", -1)])
        finance.create_index([("user_id", 1), ("created_at", -1)])
        # NEW
        watchlists.create_index("user_id", unique=True)
        positions.create_index("user_id", unique=True)
       
        emis.create_index([("user_id", 1), ("due_date", 1)])
        loans.create_index([("user_id", 1), ("created_at", -1)])

