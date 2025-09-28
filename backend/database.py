from flask_pymongo import PyMongo

mongo = PyMongo()

def init_db(app):
    mongo.init_app(app)
    # Ensure useful indexes
    with app.app_context():
        users = mongo.db.users
        expenses = mongo.db.expenses
        users.create_index("username", unique=True)
        expenses.create_index([("user_id", 1), ("created_at", -1)])
    return mongo
