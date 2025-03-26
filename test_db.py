# test_db.py
from database import get_db_connection

try:
    with get_db_connection() as conn:
        print("Database connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
