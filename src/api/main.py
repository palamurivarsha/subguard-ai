
from pathlib import Path
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pandas as pd
import mysql.connector
from fastapi import FastAPI, HTTPException

from src.api.database import get_db_connection


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = FastAPI(
    title="SubGuard AI API",
    description=(
        "AI-powered subscription detection, renewal prediction, "
        "anomaly detection, risk scoring, and free-trial reminders."
    ),
    version="0.3.0",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def read_csv(filename: str):
    """Read a processed CSV file and return JSON-compatible rows."""

    file_path = PROCESSED_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Required processed file is missing: {filename}",
        )

    try:
        df = pd.read_csv(file_path)

        # Convert pandas missing values to Python None.
        df = df.astype(object).where(pd.notna(df), None)

        return df.to_dict(orient="records")

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read {filename}: {exc}",
        ) from exc


def serialize_mysql_row(row: dict):
    """Convert MySQL values into JSON-compatible Python values."""

    result = {}

    for key, value in row.items():

        if isinstance(value, (datetime, date, time)):
            result[key] = value.isoformat()

        elif isinstance(value, timedelta):
            result[key] = str(value)

        elif isinstance(value, Decimal):
            result[key] = float(value)

        elif isinstance(value, bytes):
            result[key] = value.decode("utf-8", errors="replace")

        else:
            result[key] = value

    return result


def fetch_mysql_data(query: str, params=None):
    """Execute a read-only MySQL query and return serialized rows."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, params or ())
        rows = cursor.fetchall()

        return [serialize_mysql_row(row) for row in rows]

    except mysql.connector.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="MySQL database is unavailable.",
        ) from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# HOME AND HEALTH
# ============================================================

@app.get("/")
def home():
    return {
        "application": "SubGuard AI",
        "version": "0.3.0",
        "status": "running",
        "message": "Welcome to the SubGuard AI API",
        "documentation": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "SubGuard AI",
    }


# ============================================================
# CSV-BASED SUBSCRIPTION ENDPOINTS
# ============================================================

@app.get("/subscriptions")
def get_subscriptions():
    return read_csv("detected_subscriptions.csv")


@app.get("/predictions")
def get_predictions():
    return read_csv("next_charge_predictions.csv")


@app.get("/anomalies")
def get_anomalies():
    return read_csv("subscription_anomalies.csv")


@app.get("/risk-scores")
def get_risk_scores():
    return read_csv("renewal_risk_scores.csv")


@app.get("/explanations")
def get_explanations():
    return read_csv("validated_subscription_explanations.csv")


# ============================================================
# MYSQL SUBSCRIPTION ENDPOINTS
# ============================================================

@app.get("/db/subscriptions")
def get_db_subscriptions():

    query = """
        SELECT
            subscription_id,
            merchant_name,
            billing_frequency,
            average_amount,
            first_seen_date,
            last_seen_date,
            next_predicted_charge_date,
            next_predicted_amount,
            detection_confidence,
            status
        FROM subscriptions
        ORDER BY merchant_name
    """

    return fetch_mysql_data(query)


@app.get("/db/risk-scores")
def get_db_risk_scores():

    query = """
        SELECT
            r.risk_id,
            r.subscription_id,
            s.merchant_name,
            r.risk_score,
            r.risk_level,
            r.price_change_score,
            r.billing_irregularity_score,
            r.prediction_uncertainty_score,
            r.calculated_at
        FROM risk_scores r
        JOIN subscriptions s
            ON r.subscription_id = s.subscription_id
        ORDER BY r.risk_score DESC, s.merchant_name
    """

    return fetch_mysql_data(query)


# ============================================================
# FREE-TRIAL ENDPOINTS
# ============================================================

@app.get("/db/free-trials")
def get_db_free_trials():

    query = """
        SELECT
            trial_id,
            service_name,
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
        FROM free_trials
        ORDER BY cancellation_deadline_at_utc
    """

    return fetch_mysql_data(query)


@app.get("/db/trial-reminders")
def get_db_trial_reminders():

    query = """
        SELECT
            d.delivery_id,
            d.trial_id,
            f.service_name,
            d.cancellation_deadline_at_utc,
            d.reminder_type,
            d.delivery_status,
            d.attempt_count,
            d.updated_at_utc,
            l.sent_at_utc
        FROM trial_reminder_delivery d
        JOIN free_trials f
            ON d.trial_id = f.trial_id
        LEFT JOIN trial_reminder_log l
            ON l.trial_id = d.trial_id
           AND l.cancellation_deadline_at_utc =
               d.cancellation_deadline_at_utc
           AND l.reminder_type = d.reminder_type
        ORDER BY d.updated_at_utc DESC
    """

    return fetch_mysql_data(query)


# ============================================================
# NEW: MARK FREE TRIAL AS CANCELED
# ============================================================

@app.patch("/db/free-trials/{trial_id}/cancel")
def mark_trial_canceled(trial_id: int):
    """
    Record that the user has canceled a free trial.

    IMPORTANT:
    This updates SubGuard's internal database only.
    It does not cancel the subscription at the provider.
    """

    if trial_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Trial ID must be a positive integer.",
        )

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Lock the selected trial while updating its status.
        cursor.execute(
            """
            SELECT
                trial_id,
                service_name,
                status
            FROM free_trials
            WHERE trial_id = %s
            FOR UPDATE
            """,
            (trial_id,),
        )

        trial = cursor.fetchone()

        if trial is None:
            raise HTTPException(
                status_code=404,
                detail="Free trial not found.",
            )

        # Repeated requests are safe.
        if trial["status"] == "canceled":
            connection.commit()

            return {
                "trial_id": trial_id,
                "service_name": trial["service_name"],
                "status": "canceled",
                "message": (
                    "This trial was already marked canceled "
                    "in SubGuard AI."
                ),
            }

        if trial["status"] != "active":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only active trials can be marked canceled. "
                    f"Current status: {trial['status']}"
                ),
            )

        cursor.execute(
            """
            UPDATE free_trials
            SET status = 'canceled'
            WHERE trial_id = %s
              AND status = 'active'
            """,
            (trial_id,),
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail="Trial status changed before the update completed.",
            )

        connection.commit()

        return {
            "trial_id": trial_id,
            "service_name": trial["service_name"],
            "status": "canceled",
            "message": (
                "Trial marked canceled in SubGuard AI. "
                "Future reminders will be skipped. "
                "This does not cancel the subscription "
                "with the provider."
            ),
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise

    except mysql.connector.Error as exc:
        if connection is not None:
            connection.rollback()

        raise HTTPException(
            status_code=503,
            detail="Database operation failed while updating the trial.",
        ) from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# INDIVIDUAL SUBSCRIPTION LOOKUP
# ============================================================

@app.get("/subscriptions/{merchant_name}")
def get_subscription_by_merchant(merchant_name: str):

    subscriptions = read_csv("detected_subscriptions.csv")

    for subscription in subscriptions:

        if (
            str(subscription.get("merchant_name", "")).lower()
            == merchant_name.lower()
        ):
            return subscription

    raise HTTPException(
        status_code=404,
        detail=f"Subscription '{merchant_name}' not found.",
    )
