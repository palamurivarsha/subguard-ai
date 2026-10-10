import os

import mysql.connector
from dotenv import load_dotenv


load_dotenv()

connection = None

try:
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

    if connection.is_connected():
        print("Connected to MySQL successfully!")

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE();")

        database = cursor.fetchone()[0]

        print(f"Current database: {database}")

        cursor.close()

except mysql.connector.Error as error:
    print(f"MySQL connection failed: {error}")

finally:
    if connection and connection.is_connected():
        connection.close()
        print("MySQL connection closed.")