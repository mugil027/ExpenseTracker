# database.py
from flask_pymongo import PyMongo
import sys

mongo = PyMongo()

def init_db(app):
    uri = app.config.get("MONGO_URI")
    print("📡 Trying to connect to MongoDB:", uri, file=sys.stdout)

    mongo.init_app(app)

    try:
        # Ping the server to check connection
        mongo.db.command("ping")
        print("✅ MongoDB connected successfully!", file=sys.stdout)
    except Exception as e:
        print("❌ MongoDB connection failed:", e, file=sys.stderr)
        return  # stop setup if connection fails

    # Create collections and indexes safely
    with app.app_context():
        db = mongo.db
        if db:
            users = db.users
            expenses = db.expenses
            finance = db.finance
            watchlists = db.watchlists
            positions = db.positions
            emis = db.emis
            loans = db.loans

            # Indexes
            users.create_index("username", unique=True)
            expenses.create_index([("user_id", 1), ("created_at", -1)])
            finance.create_index([("user_id", 1), ("created_at", -1)])
            watchlists.create_index("user_id", unique=True)
            positions.create_index("user_id", unique=True)
            emis.create_index([("user_id", 1), ("due_date", 1)])
            loans.create_index([("user_id", 1), ("created_at", -1)])
            print("✅ All MongoDB collections and indexes are ready!", file=sys.stdout)
        else:
            print("⚠️ mongo.db is None — collections not initialized", file=sys.stderr)
