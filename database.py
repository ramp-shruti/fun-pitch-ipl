# database.py
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            phone VARCHAR(30) UNIQUE NOT NULL,
            name VARCHAR(50) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS group_participants (
            group_id INTEGER REFERENCES groups(id),
            participant_id INTEGER REFERENCES participants(id),
            PRIMARY KEY (group_id, participant_id)
        );
        CREATE TABLE IF NOT EXISTS active_participants (
            participant_id INTEGER PRIMARY KEY REFERENCES participants(id)
        );
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            match_name VARCHAR(20) UNIQUE NOT NULL,
            team1 VARCHAR(50) NOT NULL,
            team2 VARCHAR(50) NOT NULL,
            venue TEXT NOT NULL,
            match_time TIMESTAMP WITH TIME ZONE NOT NULL,
            cricapi_id VARCHAR(36) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            match_id INTEGER REFERENCES matches(id),
            participant_id INTEGER REFERENCES participants(id),
            group_id INTEGER REFERENCES groups(id),
            team VARCHAR(50) NOT NULL,
            is_power_play BOOLEAN DEFAULT FALSE,
            UNIQUE (match_id, participant_id, group_id)
        );
        CREATE TABLE IF NOT EXISTS results (
            match_id INTEGER PRIMARY KEY REFERENCES matches(id),
            winner VARCHAR(50) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scores (
            participant_id INTEGER REFERENCES participants(id),
            group_id INTEGER REFERENCES groups(id),
            score INTEGER DEFAULT 0,
            power_play_count INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            loss_streak INTEGER DEFAULT 0,
            PRIMARY KEY (participant_id, group_id)
        );
        CREATE TABLE IF NOT EXISTS vote_context (
            participant_id INTEGER PRIMARY KEY REFERENCES participants(id),
            match_name VARCHAR(20) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def insert_group(name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO groups (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id",
                (name, ))
            result = cur.fetchone()
            conn.commit()
            return result["id"] if result else None


def insert_participant(phone, name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO participants (phone, name) VALUES (%s, %s) ON CONFLICT (phone) DO NOTHING RETURNING id",
                (phone, name))
            result = cur.fetchone()
            conn.commit()
            return result["id"] if result else None


def link_participant_to_group(group_id, participant_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO group_participants (group_id, participant_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (group_id, participant_id))
            conn.commit()


def insert_match(match_name, team1, team2, venue, match_time, cricapi_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO matches (match_name, team1, team2, venue, match_time, cricapi_id)
                VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (match_name) DO NOTHING RETURNING id
            """, (match_name, team1, team2, venue, match_time, cricapi_id))
            result = cur.fetchone()
            conn.commit()
            return result["id"] if result else None


def fetch_existing_id(table, column, value):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {table} WHERE {column} = %s",
                        (value, ))
            result = cur.fetchone()
            return result["id"] if result else None


def activate_participant(participant_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO active_participants (participant_id) VALUES (%s) ON CONFLICT (participant_id) DO NOTHING",
                (participant_id, ))
            conn.commit()


def set_vote_context(participant_id, match_name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vote_context (participant_id, match_name)
                VALUES (%s, %s)
                ON CONFLICT (participant_id) DO UPDATE
                SET match_name = EXCLUDED.match_name, created_at = NOW()
            """, (participant_id, match_name))
            conn.commit()


def get_vote_context(participant_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT match_name FROM vote_context WHERE participant_id = %s",
                (participant_id, ))
            result = cur.fetchone()
            return result["match_name"] if result else None


def clear_vote_context(participant_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM vote_context WHERE participant_id = %s",
                        (participant_id, ))
            conn.commit()
