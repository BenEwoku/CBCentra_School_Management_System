# database/initialize_db.py
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseInitializer:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'school_management')
        }

    def initialize(self):
        """Initialize database using direct connection"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            print("✅ Connected to MySQL successfully!")
            print("Database is ready - tables will be created by models.py")
            
        except Error as e:
            print(f"❌ Error: {e}")
            raise
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

if __name__ == "__main__":
    print("🚀 Starting database initialization...")
    initializer = DatabaseInitializer()
    initializer.initialize()