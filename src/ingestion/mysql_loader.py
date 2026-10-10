from pathlib import Path
import os

import mysql.connector
import pandas as pd
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    """Create and return a MySQL connection."""

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def load_transactions():
    """Read synthetic transactions and load them into MySQL."""

    project_root = Path(__file__).resolve().parents[2]

    csv_file = (
        project_root
        / "data"
        / "synthetic"
        / "bank_transactions.csv"
    )

    print(f"Reading: {csv_file}")

    df = pd.read_csv(csv_file)

    print(f"Rows found: {len(df)}")

    # -----------------------------
    # Basic validation
    # -----------------------------

    required_columns = [
        "transaction_id",
        "transaction_date",
        "description",
        "amount",
        "transaction_type",
        "merchant_ground_truth",
        "is_subscription_ground_truth",
        "event_type_ground_truth",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # -----------------------------
    # Prepare SQL
    # -----------------------------

    insert_query = """
        INSERT INTO transactions (
            transaction_id,
            transaction_date,
            description,
            amount,
            transaction_type,
            merchant_ground_truth,
            is_subscription_ground_truth,
            event_type_ground_truth
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Makes the loader safe to rerun during development.
        cursor.execute("DELETE FROM transactions;")

        records = []

        for row in df.itertuples(index=False):

            records.append(
                (
                    row.transaction_id,
                    row.transaction_date,
                    row.description,
                    float(row.amount),
                    row.transaction_type,
                    row.merchant_ground_truth,
                    int(row.is_subscription_ground_truth),
                    row.event_type_ground_truth,
                )
            )

        cursor.executemany(
            insert_query,
            records,
        )

        connection.commit()

        print(
            f"Successfully loaded {cursor.rowcount} "
            "transactions into MySQL."
        )

    except Exception:
        if connection:
            connection.rollback()

        raise

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

            print("MySQL connection closed.")


if __name__ == "__main__":
    load_transactions()