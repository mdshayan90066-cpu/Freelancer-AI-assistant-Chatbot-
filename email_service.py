import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

def send_reminder_email(to_email: str, subject: str, body: str) -> dict:
    load_dotenv(override=True)
    sender = os.getenv("GMAIL_SENDER", "")
    app_pass = os.getenv("GMAIL_APP_PASS", "")

    if not sender or not app_pass:
        return {"success": False, "error": "Gmail credentials not configured. Set GMAIL_SENDER and GMAIL_APP_PASS in .env"}

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, app_pass)
            server.send_message(msg)

        return {"success": True, "message": f"Email sent to {to_email}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
