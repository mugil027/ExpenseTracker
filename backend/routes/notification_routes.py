# routes/notification_routes.py
from flask import Blueprint, request, jsonify
import requests
from email.mime.text import MIMEText
import os

notification_bp = Blueprint('notification_bp', __name__)

# Load environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
MAIL_SENDER = os.getenv("MAIL_SENDER", "mugilwork27@gmail.com")


@notification_bp.route('/api/notify_goal_exceeded', methods=['POST'])
def notify_goal_exceeded():
    """
    Endpoint: POST /api/notify_goal_exceeded
    Expects JSON:
    {
        "category": "Food",
        "spent": 2500,
        "goal": 2000,
        "email": "mugilwork27@gmail.com"
    }
    """
    data = request.get_json()
    category = data.get('category')
    spent = data.get('spent')
    goal = data.get('goal')
    email = data.get('email')

    # Validate input
    if not all([category, spent, goal, email]):
        return jsonify({"error": "Missing data"}), 400

    subject = f"Budget Alert: {category} Exceeded!"
    body = (
        f"Hi there,\n\n"
        f"You have exceeded your spending goal for {category}.\n"
        f"Goal: ₹{goal:.2f}\n"
        f"Spent: ₹{spent:.2f}\n\n"
        f"Please review your expenses.\n\n"
        f"— Expense Tracker"
    )

    try:
        send_email(email, subject, body)
        return jsonify({"message": "Email sent successfully"}), 200
    except Exception as e:
        print("❌ Email sending error:", e, flush=True)
        return jsonify({"error": "Failed to send email"}), 500


def send_email(to_email, subject, body):
    """
    Sends email using SendGrid API (Render-friendly, no SMTP required).
    """
    api_key = SENDGRID_API_KEY
    sender_email = MAIL_SENDER

    if not api_key:
        raise Exception("Missing SENDGRID_API_KEY in environment variables")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "personalizations": [
            {"to": [{"email": to_email}]}
        ],
        "from": {"email": sender_email, "name": "Expense Tracker"},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}]
    }

    print(f"📧 Sending email to {to_email} via SendGrid...", flush=True)

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers=headers,
        json=payload,
        timeout=10
    )

    if response.status_code != 202:
        raise Exception(f"SendGrid API Error {response.status_code}: {response.text}")

    print("✅ Email sent successfully through SendGrid!", flush=True)
