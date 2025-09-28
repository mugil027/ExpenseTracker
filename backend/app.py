from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from database import init_db
from routes.auth_routes import auth_bp, bcrypt
from routes.expense_routes import expense_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    jwt = JWTManager(app)
    bcrypt.init_app(app)
    init_db(app)

    # CORS
    # Explicitly allow requests from the local file system
    CORS(app, resources={r"*": {"origins": [
        "file://",  # Allows local file access for development
        app.config.get("CORS_ORIGINS", "*")
    ]}})

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(expense_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
