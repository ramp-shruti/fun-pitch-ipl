# check_db.py
from database import get_db_connection


def verify_data():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Groups
            cur.execute("SELECT COUNT(*) FROM groups")
            print("Total Groups:", cur.fetchone()["count"])
            cur.execute("SELECT * FROM groups")
            print("Groups:", cur.fetchall())

            # Participants
            cur.execute("SELECT COUNT(*) FROM participants")
            print("Total Participants:", cur.fetchone()["count"])
            cur.execute("SELECT * FROM participants LIMIT 5")
            print("Sample Participants (first 5):", cur.fetchall())

            # Matches
            cur.execute("SELECT COUNT(*) FROM matches")
            print("Total Matches:", cur.fetchone()["count"])
            cur.execute("SELECT * FROM matches LIMIT 5")
            print("Sample Matches (first 5):", cur.fetchall())


if __name__ == "__main__":
    verify_data()
