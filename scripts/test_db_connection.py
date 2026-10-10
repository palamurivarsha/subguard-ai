from getpass import getpass
import mysql.connector

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
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT DATABASE(), COUNT(*) FROM transactions")
        database, count = cursor.fetchone()
        print(f"Connected to: {database}")
        print(f"Transactions currently stored: {count}")
    finally:
        cursor.close()
finally:
    connection.close()