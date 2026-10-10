import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


def main():
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    address = os.getenv("GMAIL_ADDRESS", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")

    if not address or not password:
        raise ValueError(
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in your root .env file."
        )

    message = EmailMessage()
    message["Subject"] = "SubGuard AI — Test Email"
    message["From"] = address
    message["To"] = address
    message.set_content(
        "Your SubGuard AI Gmail connection works!\n\n"
        "This is a test email. Free-trial reminders are the next step."
    )

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(address, password)
        server.send_message(message)

    print("Gmail accepted the test email. Check your Inbox and Spam folder.")


if __name__ == "__main__":
    main()