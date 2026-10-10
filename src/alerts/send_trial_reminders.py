
import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import mysql.connector
from dotenv import load_dotenv

from gmail_sender import send_email


# ==================================================
# CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Keep Gmail delivery restricted to the existing demo trial.
DEMO_SERVICE = "SubGuard Gmail Test Trial"


def utc_now():
    """Return UTC time as a naive datetime for MySQL UTC DATETIME fields."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "subguard_ai"),
    )


# ==================================================
# REMINDER SCHEDULING
# ==================================================

def get_applicable_reminder(deadline, now):
    """
    Choose only the latest applicable reminder.

    - More than 3 days remaining: nothing due
    - Between 3 days and 1 day remaining: 3_day
    - Within 1 day of deadline: 1_day
    - At or after deadline: nothing due

    This permits catch-up reminders without sending
    both reminder types during the same run.
    """
    if now >= deadline:
        return None

    one_day_before = deadline - timedelta(days=1)
    three_days_before = deadline - timedelta(days=3)

    if now >= one_day_before:
        return "1_day"

    if now >= three_days_before:
        return "3_day"

    return None


def get_existing_reminder(connection, trial, reminder_type):
    """Check whether a reminder has already been claimed."""
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT delivery_status, attempt_count
            FROM trial_reminder_delivery
            WHERE trial_id = %s
              AND cancellation_deadline_at_utc = %s
              AND reminder_type = %s
            """,
            (
                trial["trial_id"],
                trial["cancellation_deadline_at_utc"],
                reminder_type,
            ),
        )

        return cursor.fetchone()

    finally:
        cursor.close()


# ==================================================
# DUPLICATE PROTECTION
# ==================================================

def claim_reminder(connection, trial, reminder_type):
    """
    Atomically claim a reminder using the existing
    MySQL unique index.

    An existing claim is never automatically retried,
    because SMTP delivery may have occurred even if
    the application did not finish recording it.
    """
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT IGNORE INTO trial_reminder_delivery (
                trial_id,
                cancellation_deadline_at_utc,
                reminder_type,
                delivery_status,
                attempt_count,
                updated_at_utc
            )
            VALUES (%s, %s, %s, 'sending', 1, %s)
            """,
            (
                trial["trial_id"],
                trial["cancellation_deadline_at_utc"],
                reminder_type,
                utc_now(),
            ),
        )

        claimed = cursor.rowcount == 1
        connection.commit()
        return claimed

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


# ==================================================
# DELIVERY STATUS
# ==================================================

def mark_status(connection, trial, reminder_type, status, error=None):
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE trial_reminder_delivery
            SET delivery_status = %s,
                last_error = %s,
                updated_at_utc = %s
            WHERE trial_id = %s
              AND cancellation_deadline_at_utc = %s
              AND reminder_type = %s
              AND delivery_status = 'sending'
            """,
            (
                status,
                error,
                utc_now(),
                trial["trial_id"],
                trial["cancellation_deadline_at_utc"],
                reminder_type,
            ),
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def record_success(connection, trial, reminder_type):
    """
    Record SMTP acceptance and update delivery status
    in one MySQL transaction.
    """
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO trial_reminder_log (
                trial_id,
                cancellation_deadline_at_utc,
                reminder_type,
                recipient_email,
                sent_at_utc
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                trial["trial_id"],
                trial["cancellation_deadline_at_utc"],
                reminder_type,
                trial["reminder_email"],
                utc_now(),
            ),
        )

        cursor.execute(
            """
            UPDATE trial_reminder_delivery
            SET delivery_status = 'sent',
                updated_at_utc = %s,
                last_error = NULL
            WHERE trial_id = %s
              AND cancellation_deadline_at_utc = %s
              AND reminder_type = %s
              AND delivery_status = 'sending'
            """,
            (
                utc_now(),
                trial["trial_id"],
                trial["cancellation_deadline_at_utc"],
                reminder_type,
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "Reminder claim is no longer in sending status."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


# ==================================================
# EMAIL CONTENT
# ==================================================

def build_email(trial, reminder_type):
    deadline = trial["cancellation_deadline_at_utc"]

    subject = (
        f"[TEST] SubGuard AI - "
        f"{reminder_type} subscription reminder"
    )

    body = (
        "This is a SubGuard AI demonstration email.\n\n"
        f"Service: {trial['service_name']}\n"
        f"Reminder: {reminder_type}\n"
        f"Cancellation deadline (UTC): {deadline}\n"
        f"Expected renewal: {trial['currency']} "
        f"{trial['renewal_amount']} "
        f"/ {trial['billing_period']}\n\n"
        "If this were a real subscription, you would need "
        "to cancel through the provider before its deadline "
        "to avoid an unwanted renewal.\n\n"
        "This demo does not create a real subscription charge.\n\n"
        "-- SubGuard AI"
    )

    return subject, body


# ==================================================
# MAIN REMINDER ENGINE
# ==================================================

def run(dry_run=False, as_of=None):
    """
    Process reminders.

    dry_run=True:
        Read-only preview. No emails or database writes.

    as_of:
        Optional UTC datetime for dry-run testing only.
        Never permitted for live sending.
    """
    if as_of is not None and not dry_run:
        raise ValueError("--as-of can only be used with --dry-run.")

    now = as_of if as_of is not None else utc_now()

    print("\n========== SUBGUARD GMAIL REMINDER DELIVERY ==========")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Evaluation time (UTC): {now}")

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                trial_id,
                service_name,
                reminder_email,
                cancellation_deadline_at_utc,
                renewal_amount,
                currency,
                billing_period,
                status
            FROM free_trials
            WHERE status = 'active'
              AND service_name = %s
            """,
            (DEMO_SERVICE,),
        )

        trials = cursor.fetchall()
        print(f"Demo trials found: {len(trials)}")

        for trial in trials:
            trial_id = trial["trial_id"]
            deadline = trial["cancellation_deadline_at_utc"]

            print(f"\nTrial: {trial['service_name']}")
            print(f"Trial ID: {trial_id}")
            print(f"Cancellation deadline (UTC): {deadline}")

            if now >= deadline:
                print("SKIPPED - Cancellation deadline passed.")
                continue

            reminder_type = get_applicable_reminder(deadline, now)

            if reminder_type is None:
                print("SKIPPED - No reminder due yet.")
                continue

            print(f"Applicable reminder: {reminder_type}")

            existing = get_existing_reminder(
                connection,
                trial,
                reminder_type,
            )

            # ------------------------------------------
            # DRY-RUN MODE
            # ------------------------------------------
            if dry_run:
                if existing:
                    print(
                        "DRY RUN - Already claimed: "
                        f"{reminder_type}, "
                        f"status={existing['delivery_status']}, "
                        f"attempts={existing['attempt_count']}"
                    )
                else:
                    print(
                        f"DRY RUN - Would send {reminder_type} "
                        f"reminder to the configured recipient."
                    )

                continue

            # ------------------------------------------
            # LIVE MODE
            # ------------------------------------------
            if existing:
                print(
                    f"SKIPPED - Reminder already claimed: "
                    f"{reminder_type}"
                )
                continue

            claimed = claim_reminder(
                connection,
                trial,
                reminder_type,
            )

            if not claimed:
                print(
                    "SKIPPED - Another process already claimed "
                    f"the {reminder_type} reminder."
                )
                continue

            subject, body = build_email(
                trial,
                reminder_type,
            )

            try:
                send_email(
                    trial["reminder_email"],
                    subject,
                    body,
                )

            except Exception as exc:
                # SMTP failures may be ambiguous. Do not retry
                # automatically or risk duplicate messages.
                mark_status(
                    connection,
                    trial,
                    reminder_type,
                    "uncertain",
                    str(exc)[:1000],
                )

                print(
                    f"UNCERTAIN - Manual delivery review needed: {exc}"
                )
                continue

            try:
                record_success(
                    connection,
                    trial,
                    reminder_type,
                )

                print(
                    f"SENT - Trial {trial_id} ({reminder_type})"
                )

            except Exception as exc:
                # Claim remains in the database, preventing
                # an automatic duplicate send.
                print(
                    "WARNING - Gmail accepted the message, "
                    f"but database logging failed: {exc}"
                )

        print("\n========== DELIVERY RUN COMPLETE ==========")

    finally:
        cursor.close()
        connection.close()


# ==================================================
# COMMAND-LINE OPTIONS
# ==================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SubGuard AI trial reminder sender"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview reminders without emails or database writes.",
    )

    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help=(
            "Simulated UTC time for dry-run testing only. "
            "Format: YYYY-MM-DDTHH:MM:SS"
        ),
    )

    args = parser.parse_args()

    simulated_time = None

    if args.as_of:
        if not args.dry_run:
            parser.error("--as-of requires --dry-run.")

        try:
            simulated_time = datetime.strptime(
                args.as_of,
                "%Y-%m-%dT%H:%M:%S",
            )
        except ValueError:
            parser.error(
                "--as-of must use YYYY-MM-DDTHH:MM:SS"
            )

    run(
        dry_run=args.dry_run,
        as_of=simulated_time,
    )
