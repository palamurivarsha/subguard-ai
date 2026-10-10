
from pathlib import Path
import os
import mysql.connector
from dotenv import load_dotenv

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# MySQL configuration
host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME", "subguard_ai")

if not user:
    raise ValueError(
        "DB_USER is missing from your .env file."
    )

connection = mysql.connector.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
)

cursor = connection.cursor()

try:
    print("\n========== REMINDER LOG INDEXES ==========")

    cursor.execute(
        "SHOW INDEX FROM trial_reminder_log"
    )

    indexes = cursor.fetchall()

    for index in indexes:
        print(index)

    print("\n========== TABLE INSPECTION COMPLETE ==========")

finally:
    cursor.close()
    connection.close()
