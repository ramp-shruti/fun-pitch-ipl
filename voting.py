# voting.py
from database import get_db_connection
from datetime import datetime
from zoneinfo import ZoneInfo


def record_vote(phone, match_name, team, is_power_play):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM participants WHERE phone = %s",
                        (phone, ))
            participant = cur.fetchone()
            if not participant:
                return False
            participant_id = participant["id"]

            cur.execute(
                "SELECT id, team1, team2, match_time FROM matches WHERE match_name = %s",
                (match_name, ))
            match = cur.fetchone()
            if not match or datetime.now(
                    ZoneInfo("UTC")) > match["match_time"]:
                return False

            if team not in (match["team1"], match["team2"]):
                return False

            cur.execute(
                "SELECT group_id FROM group_participants WHERE participant_id = %s",
                (participant_id, ))
            group_ids = [row["group_id"] for row in cur.fetchall()]

            for group_id in group_ids:
                cur.execute(
                    """
                    INSERT INTO votes (match_id, participant_id, group_id, team, is_power_play)
                    VALUES (%s, %s, %s, %s, %s) ON CONFLICT (match_id, participant_id, group_id) DO UPDATE
                    SET team = EXCLUDED.team, is_power_play = EXCLUDED.is_power_play
                """, (match["id"], participant_id, group_id, team,
                      is_power_play))
            conn.commit()
            return True
