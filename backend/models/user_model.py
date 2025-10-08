from database import mongo

def create_user(username: str, password_hash: str):
    return mongo.db.users.insert_one({
        "username": username,
        "password": password_hash,
    })

def find_user_by_username(username: str):
    return mongo.db.users.find_one({"username": username})

def find_user_by_id(user_id):
    return mongo.db.users.find_one({"_id": user_id})
