
from pathlib import Path
from decimal import Decimal
import os

import pandas as pd
import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

SUBSCRIPTIONS_PATH = (
    PROJECT_ROOT / "data/processed/detected_subscriptions.csv"
)

PREDICTIONS_PATH = (
    PROJECT_ROOT / "data/processed/next_charge_predictions.csv"
)


def clean_value(value):
    if pd.isna(value):
        return None
    return value


def decimal_value(value):
    if pd.isna(value):
        return None
    return Decimal(str(value))


def date_value(value):
    if pd.isna(value):
        return None
    return pd.to_datetime(value).date()


def load_subscriptions():
    subscriptions = pd.read_csv(SUBSCRIPTIONS_PATH)
    predictions = pd.read_csv(PREDICTIONS_PATH)

    merged = subscriptions.merge(
        predictions[
            [
                "merchant_name",
                "predicted_next_charge_date",
                "predicted_next_amount",
            ]
        ],
        on="merchant_name",
        how="left",
        validate="one_to_one",
    )

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "subguard_ai"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    cursor = connection.cursor()

    print("\n========== SUBGUARD SUBSCRIPTION LOADER ==========")

    inserted = 0
    updated = 0

    try:
        for _, row in merged.iterrows():
            merchant = str(row["merchant_name"])

            cursor.execute(
                """
                SELECT subscription_id
                FROM subscriptions
                WHERE merchant_name = %s
                ORDER BY subscription_id
                """,
                (merchant,),
            )

            existing = cursor.fetchall()

            if len(existing) > 1:
                raise ValueError(
                    f"Multiple subscriptions found for {merchant}. "
                    "Resolve duplicates before loading."
                )

            values = (
                clean_value(row["billing_frequency"]),
                decimal_value(row["average_amount"]),
                date_value(row["first_seen_date"]),
                date_value(row["last_seen_date"]),
                date_value(row["predicted_next_charge_date"]),
                decimal_value(row["predicted_next_amount"]),
                decimal_value(row["detection_confidence"]),
            )

            if existing:
                subscription_id = existing[0][0]

                cursor.execute(
                    """
                    UPDATE subscriptions
                    SET billing_frequency = %s,
                        average_amount = %s,
                        first_seen_date = %s,
                        last_seen_date = %s,
                        next_predicted_charge_date = %s,
                        next_predicted_amount = %s,
                        detection_confidence = %s
                    WHERE subscription_id = %s
                    """,
                    values + (subscription_id,),
                )

                updated += 1

            else:
                cursor.execute(
                    """
                    INSERT INTO subscriptions (
                        merchant_name,
                        billing_frequency,
                        average_amount,
                        first_seen_date,
                        last_seen_date,
                        next_predicted_charge_date,
                        next_predicted_amount,
                        detection_confidence,
                        status
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, 'active'
                    )
                    """,
                    (merchant,) + values,
                )

                inserted += 1

        connection.commit()

        print(f"Inserted subscriptions: {inserted}")
        print(f"Updated subscriptions: {updated}")

        cursor.execute(
            """
            SELECT
                subscription_id,
                merchant_name,
                billing_frequency,
                next_predicted_charge_date,
                next_predicted_amount
            FROM subscriptions
            ORDER BY merchant_name
            """
        )

        print("\nSubscriptions in MySQL:")

        for record in cursor.fetchall():
            print(record)

        print("\n========== LOADING COMPLETE ==========")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    load_subscriptions()
