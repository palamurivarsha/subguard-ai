import csv
from datetime import date
from decimal import Decimal
from getpass import getpass
from pathlib import Path
from uuid import UUID

import mysql.connector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "synthetic" / "bank_transactions.csv"

rows = []
seen_ids = set()

with CSV_PATH.open(newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for line_number, row in enumerate(reader, start=2):
        try:
            transaction_id = str(UUID(row["transaction_id"].strip()))
            transaction_date = date.fromisoformat(row["transaction_date"])
            amount = Decimal(row["amount"])
            description = row["description"].strip()
            transaction_type = row["transaction_type"].strip().lower()
            merchant = row["merchant_ground_truth"].strip() or None
            label = int(row["is_subscription_ground_truth"])

            if transaction_id in seen_ids:
                raise ValueError("Duplicate transaction ID in CSV")
            if not amount.is_finite() or amount != amount.quantize(Decimal("0.01")):
                raise ValueError("Amount must have at most two decimal places")
            if abs(amount) >= Decimal("10000000000"):
                raise ValueError("Amount exceeds the database column limit")
            if not description or not transaction_type:
                raise ValueError("Description and transaction type are required")
            if len(transaction_type) > 20 or (merchant and len(merchant) > 255):
                raise ValueError("Text exceeds the database column limit")
            if label not in (0, 1):
                raise ValueError("Subscription label must be 0 or 1")

            seen_ids.add(transaction_id)
            rows.append((
                transaction_id, transaction_date, description, amount,
                transaction_type, merchant, label,
            ))
        except (ValueError, ArithmeticError, KeyError) as error:
            raise ValueError(f"Invalid CSV row {line_number}: {error}") from error

if not rows:
    raise ValueError("CSV contains no transactions")

print(f"Validated CSV rows: {len(rows)}")

username = input("MySQL username [root]: ").strip() or "root"
password = getpass("MySQL password: ")

connection = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user=username,
    password=password,
    database="subguard_ai",
    connection_timeout=10,
    autocommit=False,
)

try:
    with connection.cursor() as cursor:
        # Existing IDs are left unchanged when the script is rerun.
        sql = """
            INSERT INTO transactions (
                transaction_id, transaction_date, description, amount,
                transaction_type, merchant_ground_truth,
                is_subscription_ground_truth
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE transaction_id = transactions.transaction_id
        """
        cursor.executemany(sql, rows)
        connection.commit()

        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(is_subscription_ground_truth), 0)
            FROM transactions
        """)
        total, subscriptions = cursor.fetchone()
        print("CSV load completed.")
        print(f"Total transactions in database: {total}")
        print(f"Subscription transactions in database: {subscriptions}")
except Exception:
    connection.rollback()
    raise
finally:
    connection.close()