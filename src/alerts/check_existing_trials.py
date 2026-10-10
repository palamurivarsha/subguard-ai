
from pathlib import Path
import os
import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

connection = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "subguard_ai"),
)

cursor = connection.cursor(dictionary=True)

try:
    print("\n========== EXISTING FREE TRIALS ==========")

    cursor.execute("""
        SELECT
            trial_id,
            service_name,
            trial_start_at_utc,
            trial_end_at_utc,
            cancellation_deadline_at_utc,
            renewal_amount,
            currency,
            billing_period,
            status
        FROM free_trials
        ORDER BY trial_id
    """)

    trials = cursor.fetchall()

    print(f"Total trials in database: {len(trials)}")

    for trial in trials:
        print("\n------------------------------")
        for key, value in trial.items():
            print(f"{key}: {value}")

    print("\n========== INSPECTION COMPLETE ==========")

finally:
    cursor.close()
    connection.close()
