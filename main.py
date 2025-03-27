# main.py
from setup import setup_data
from app import app

if __name__ == "__main__":
    print("[MAIN] Initializing bot setup...")
    setup_data()  # Initial setup
    print("[MAIN] Bot setup completed, starting Flask app...")
    app.run(host="0.0.0.0", port=8080)
