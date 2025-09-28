from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from models.user_model import create_user, find_user_by_username

bcrypt = Bcrypt()
auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/signup")
def signup():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify({"msg": "username and password are required"}), 400

    if find_user_by_username(username):
        return jsonify({"msg": "User already exists"}), 400

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    create_user(username, pw_hash)
    return jsonify({"msg": "Signup successful"}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = find_user_by_username(username)
    if not user:
        return jsonify({"msg": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"msg": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user["_id"]))
    return jsonify({"token": token}), 200
