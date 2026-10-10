
from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv
import os
import smtplib

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def send_email(recipient, subject, body):
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not password:
        raise ValueError(
            "GMAIL_ADDRESS or GMAIL_APP_PASSWORD is missing."
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)

    print("Email accepted by Gmail SMTP server.")


if __name__ == "__main__":
    recipient = os.getenv("GMAIL_ADDRESS")

    subject = "[TEST] SubGuard AI Email Notification"

    body = """
This is a test email from SubGuard AI.

Your Gmail notification integration is working.

This is only a demonstration.
No real subscription charge is scheduled.

-- SubGuard AI
"""

    send_email(recipient, subject, body)
