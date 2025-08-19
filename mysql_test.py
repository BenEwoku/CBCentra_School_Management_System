import mysql.connector

# Replace with your MySQL credentials
config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'benewoku14'
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    cursor.execute("CREATE DATABASE school_management")
    print("✅ Database 'school_management' created successfully.")

    cursor.close()
    conn.close()
except mysql.connector.Error as err:
    print(f"❌ Error: {err}")
