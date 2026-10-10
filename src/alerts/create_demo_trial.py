
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def create_demo_trial():
    recipient = os.getenv("GMAIL_ADDRESS")

    if not recipient:
        raise ValueError("GMAIL_ADDRESS is missing from .env")

    now = datetime.now(timezone.utc)

    # Set the cancellation deadline to 3 days from now,
    # so the 3-day reminder is immediately due.
    deadline = now + timedelta(days=3)

    # MySQL DATETIME columns store naive UTC values.
    start_utc = now.replace(tzinfo=None)
    deadline_utc = deadline.replace(tzinfo=None)

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "subguard_ai"),
    )

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO free_trials (
                service_name,
                reminder_email,
                trial_start_at_utc,
                trial_end_at_utc,
                cancellation_deadline_at_utc,
                user_timezone,
                renewal_amount,
                currency,
                billing_period,
                cancellation_url,
                status,
                created_at_utc
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """, (
            "SubGuard Gmail Test Trial",
            recipient,
            start_utc,
            deadline_utc,
            deadline_utc,
            "America/Chicago",
            9.99,
            "USD",
            "monthly",
            None,
            "active",
            start_utc,
        ))

        connection.commit()

        print("\n========== DEMO TRIAL CREATED ==========")
        print(f"Trial ID: {cursor.lastrowid}")
        print("Service: SubGuard Gmail Test Trial")
        print(f"Cancellation deadline (UTC): {deadline_utc}")
        print(f"Recipient: {recipient}")
        print("Status: active")
        print("\nNo email sent.")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    create_demo_trial()
