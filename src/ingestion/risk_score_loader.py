
from pathlib import Path
from decimal import Decimal
import os

import pandas as pd
import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

RISK_SCORES_PATH = (
    PROJECT_ROOT / "data/processed/renewal_risk_scores.csv"
)

ANOMALIES_PATH = (
    PROJECT_ROOT / "data/processed/subscription_anomalies.csv"
)


def load_risk_scores():
    scores = pd.read_csv(RISK_SCORES_PATH)
    anomalies = pd.read_csv(ANOMALIES_PATH)

    required_columns = {
        "merchant_name",
        "as_of_date",
        "risk_score",
        "risk_level",
        "confidence_score",
    }

    missing = required_columns - set(scores.columns)

    if missing:
        raise ValueError(
            f"Missing risk score columns: {sorted(missing)}"
        )

    if scores["merchant_name"].duplicated().any():
        raise ValueError(
            "Duplicate merchant names found in risk score CSV."
        )

    # Identify anomaly categories for each merchant.
    anomaly_types_by_merchant = (
        anomalies.groupby("merchant_name")["anomaly_type"]
        .apply(set)
        .to_dict()
    )

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "subguard_ai"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    cursor = connection.cursor()

    inserted = 0
    updated = 0

    print("\n========== SUBGUARD RISK SCORE LOADER ==========")

    try:
        for _, row in scores.iterrows():
            merchant = str(row["merchant_name"])
            as_of_date = pd.to_datetime(
                row["as_of_date"]
            ).date()

            cursor.execute(
                """
                SELECT subscription_id
                FROM subscriptions
                WHERE merchant_name = %s
                """,
                (merchant,),
            )

            subscription_rows = cursor.fetchall()

            if len(subscription_rows) != 1:
                raise ValueError(
                    f"Expected one subscription for {merchant}; "
                    f"found {len(subscription_rows)}."
                )

            subscription_id = subscription_rows[0][0]

            anomaly_types = anomaly_types_by_merchant.get(
                merchant, set()
            )

            # These values match our current scoring rules.
            price_change_score = (
                15 if "price_increase" in anomaly_types else 0
            )

            billing_irregularity_score = (
                15 if "duplicate_charge" in anomaly_types else 0
            )

            if (
                "unusual_amount" in anomaly_types
                and "price_increase" not in anomaly_types
            ):
                billing_irregularity_score += 10

            prediction_uncertainty_score = int(
                row["confidence_score"]
            )

            values = (
                Decimal(str(row["risk_score"])),
                str(row["risk_level"]),
                Decimal(str(price_change_score)),
                Decimal(str(billing_irregularity_score)),
                Decimal(str(prediction_uncertainty_score)),
            )

            # The existing schema has no as_of_date column.
            # Keep one latest score per subscription rather than
            # creating duplicate rows on repeated runs.
            cursor.execute(
                """
                SELECT risk_id
                FROM risk_scores
                WHERE subscription_id = %s
                ORDER BY risk_id
                """,
                (subscription_id,),
            )

            existing = cursor.fetchall()

            if len(existing) > 1:
                raise ValueError(
                    f"Multiple risk score rows already exist "
                    f"for subscription_id={subscription_id}."
                )

            if existing:
                risk_id = existing[0][0]

                cursor.execute(
                    """
                    UPDATE risk_scores
                    SET risk_score = %s,
                        risk_level = %s,
                        price_change_score = %s,
                        billing_irregularity_score = %s,
                        prediction_uncertainty_score = %s,
                        calculated_at = CURRENT_TIMESTAMP
                    WHERE risk_id = %s
                    """,
                    values + (risk_id,),
                )

                updated += 1

            else:
                cursor.execute(
                    """
                    INSERT INTO risk_scores (
                        subscription_id,
                        risk_score,
                        risk_level,
                        price_change_score,
                        billing_irregularity_score,
                        prediction_uncertainty_score
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (subscription_id,) + values,
                )

                inserted += 1

        connection.commit()

        print(f"Inserted risk scores: {inserted}")
        print(f"Updated risk scores: {updated}")

        cursor.execute(
            """
            SELECT
                s.merchant_name,
                r.risk_score,
                r.risk_level,
                r.price_change_score,
                r.billing_irregularity_score,
                r.prediction_uncertainty_score
            FROM risk_scores r
            JOIN subscriptions s
                ON r.subscription_id = s.subscription_id
            ORDER BY r.risk_score DESC, s.merchant_name
            """
        )

        print("\nRisk scores stored in MySQL:")

        for record in cursor.fetchall():
            print(record)

        print("\n========== RISK SCORE LOADING COMPLETE ==========")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    load_risk_scores()
