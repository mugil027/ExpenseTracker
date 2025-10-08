# routes/finance_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import mongo

finance_bp = Blueprint("finance_bp", __name__)

@finance_bp.route("/api/finance", methods=["GET"])
@jwt_required()
def get_finance():
    user_id = get_jwt_identity()
    doc = mongo.db.finance.find_one({"user_id": user_id}) or {}
    return jsonify({
        "assets": doc.get("assets", []),
        "liabilities": doc.get("liabilities", []),
        "snapshots": doc.get("snapshots", [])
    }), 200

@finance_bp.route("/api/finance", methods=["POST"])
@jwt_required()
def save_finance():
    user_id = get_jwt_identity()
    data = request.get_json()
    mongo.db.finance.update_one(
        {"user_id": user_id},
        {"$set": data},
        upsert=True
    )
    return jsonify({"message": "Finance data saved"}), 200
