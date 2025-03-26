# main.py
from setup import setup_data
from app import app

if __name__ == "__main__":
    setup_data()  # Initial setup
    app.run(host="0.0.0.0", port=8080)  # Start Flask app
