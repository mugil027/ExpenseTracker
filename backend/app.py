from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from database import init_db, mongo
from routes.auth_routes import auth_bp, bcrypt
from routes.expense_routes import expense_bp
from routes.notification_routes import notification_bp
from routes.finance_routes import finance_bp
from routes.investment_routes import investment_bp
from routes.emi_routes import emi_bp

# ✅ NEW imports for scheduler + timezone handling
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
import pytz

from dotenv import load_dotenv
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Extensions ---
    jwt = JWTManager(app)
    bcrypt.init_app(app)
    init_db(app)

    # --- CORS ---
    CORS(app, resources={r"*": {"origins": [
        "file://",  # for local dev (index.html)
        app.config.get("CORS_ORIGINS", "*")
    ]}})

    # --- Blueprints ---
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(expense_bp, url_prefix="/api")
    app.register_blueprint(notification_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(investment_bp)
    app.register_blueprint(emi_bp)

    # --- Health check route ---
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # -----------------------------------------------------
    # 🔔 Daily Email Scheduler for EMIs (9:00 AM IST)
    # -----------------------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    scheduler = BackgroundScheduler(timezone=ist)

    from routes.notification_routes import send_email  # Reuse your SMTP sender

    def send_all_due_emails():
        now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
        start = now_utc + timedelta(days=3)
        end = start + timedelta(days=1)

        for user in mongo.db.users.find({}):
            email = user.get("username")  # assuming username = email
            user_id = str(user["_id"])
            if not email:
                continue

            items = list(mongo.db.emis.find({
                "user_id": user_id,
                "due_date": {"$gte": start, "$lt": end},
                "status": {"$ne": "paid"}
            }))

            for it in items:
                title = it["title"]
                amt = it["amount"]
                dt = it["due_date"].date().isoformat()
                subject = f"EMI Reminder: {title} due on {dt}"
                body = f"Hey! Your {title} of ₹{amt:.2f} is due on {dt}. Don’t forget to pay on time!"
                try:
                    send_email(email, subject, body)
                except Exception as e:
                    print("⚠️ Email send failed:", e)

    # Schedule it daily at 9:00 AM IST
    scheduler.add_job(send_all_due_emails, "cron", hour=9, minute=0)
    scheduler.start()

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
