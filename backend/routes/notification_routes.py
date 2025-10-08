# routes/notification_routes.py
from flask import Blueprint, request, jsonify
import smtplib
from email.mime.text import MIMEText
import os

notification_bp = Blueprint('notification_bp', __name__)

@notification_bp.route('/api/notify_goal_exceeded', methods=['POST'])
def notify_goal_exceeded():
    data = request.get_json()
    category = data.get('category')
    spent = data.get('spent')
    goal = data.get('goal')
    email = data.get('email')

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
        print("Email sending error:", e)
        return jsonify({"error": "Failed to send email"}), 500


def send_email(to_email, subject, body):
    sender_email = os.getenv("SENDER_EMAIL", "yourmail@gmail.com")
    sender_password = os.getenv("SENDER_PASS", "yourapppassword")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)
