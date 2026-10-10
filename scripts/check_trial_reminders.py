from datetime import timedelta, timezone
from getpass import getpass
from zoneinfo import ZoneInfo

import mysql.connector


def main():
    username = input("MySQL username [root]: ").strip() or "root"
    password = getpass("MySQL password: ")

    connection = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user=username,
        password=password,
        database="subguard_ai",
        connection_timeout=10,
    )

    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT UTC_TIMESTAMP() AS now_utc")
            now = cursor.fetchone()["now_utc"]

            cursor.execute(
                """
                SELECT *
                FROM free_trials
                WHERE status = 'active'
                  AND cancellation_deadline_at_utc > %s
                  AND cancellation_deadline_at_utc <= %s
                ORDER BY cancellation_deadline_at_utc
                """,
                (now, now + timedelta(days=3)),
            )
            trials = cursor.fetchall()

        print(f"\nTrials needing a reminder: {len(trials)}")

        for trial in trials:
            deadline = trial["cancellation_deadline_at_utc"]
            remaining = deadline - now
            reminder = (
                "1-day reminder"
                if remaining <= timedelta(days=1)
                else "3-day reminder"
            )

            local_deadline = deadline.replace(
                tzinfo=timezone.utc
            ).astimezone(ZoneInfo(trial["user_timezone"]))

            print(f"\nService: {trial['service_name']}")
            print(f"Reminder: {reminder}")
            print(
                f"Expected charge: {trial['currency']} "
                f"{trial['renewal_amount']} / {trial['billing_period']}"
            )
            print(
                "Cancel before: "
                f"{local_deadline:%Y-%m-%d %I:%M %p %Z}"
            )
            print(f"Recipient: {trial['reminder_email']}")
            print(f"Cancellation link: {trial['cancellation_url']}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()