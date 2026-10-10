
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def check_reminders():
    print("\n========== SUBGUARD MYSQL REMINDER ENGINE ==========")

    now_utc = datetime.now(timezone.utc)
    print(f"Current UTC time: {now_utc.isoformat()}")

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "subguard_ai"),
    )

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                trial_id,
                service_name,
                cancellation_deadline_at_utc,
                renewal_amount,
                currency,
                billing_period,
                status
            FROM free_trials
            WHERE status = 'active'
        """)

        trials = cursor.fetchall()

        print(f"Active trial records: {len(trials)}")

        for trial in trials:
            deadline = trial["cancellation_deadline_at_utc"]

            # MySQL DATETIME values are stored as UTC.
            deadline = deadline.replace(tzinfo=timezone.utc)

            if deadline <= now_utc:
                print(
                    f"SKIPPED - Deadline passed: "
                    f"{trial['service_name']}"
                )
                continue

            time_remaining = deadline - now_utc

            # Check whether each reminder is due within
            # a one-hour window after its scheduled time.
            for days_before, reminder_type in [
                (3, "3_day"),
                (1, "1_day"),
            ]:
                reminder_at = deadline - timedelta(
                    days=days_before
                )

                if not (
                    reminder_at <= now_utc
                    < reminder_at + timedelta(hours=1)
                ):
                    continue

                cursor.execute("""
                    SELECT reminder_id
                    FROM trial_reminder_log
                    WHERE trial_id = %s
                      AND cancellation_deadline_at_utc = %s
                      AND reminder_type = %s
                    LIMIT 1
                """, (
                    trial["trial_id"],
                    trial["cancellation_deadline_at_utc"],
                    reminder_type,
                ))

                existing = cursor.fetchone()

                if existing:
                    print(
                        f"SKIPPED - Already logged: "
                        f"{trial['service_name']} "
                        f"({reminder_type})"
                    )
                    continue

                print(
                    f"DRY RUN - Reminder due: "
                    f"{trial['service_name']} "
                    f"({reminder_type})"
                )

                print(
                    f"Amount: {trial['currency']} "
                    f"{trial['renewal_amount']}"
                )

        print("\nNo emails sent. Database unchanged.")
        print("\n========== REMINDER CHECK COMPLETE ==========")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    check_reminders()
