# voting.py
from database import get_db_connection
from datetime import datetime
from zoneinfo import ZoneInfo


def record_vote(phone, match_name, team, is_power_play):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch participant ID
            cur.execute("SELECT id FROM participants WHERE phone = %s",
                        (phone, ))
            participant = cur.fetchone()
            if not participant:
                print(f"[VOTING] Participant not found for phone: {phone}")
                return False
            participant_id = participant["id"]
            print(
                f"[VOTING] Found participant: phone={phone}, participant_id={participant_id}"
            )

            # Fetch match details
            cur.execute(
                "SELECT id, team1, team2, match_time FROM matches WHERE match_name = %s",
                (match_name, ))
            match = cur.fetchone()
            if not match:
                print(f"[VOTING] Match not found for match_name: {match_name}")
                return False
            if datetime.now(ZoneInfo("UTC")) > match["match_time"]:
                print(
                    f"[VOTING] Match {match_name} has already started at {match['match_time']}"
                )
                return False

            # Validate team
            if team not in (match["team1"], match["team2"]):
                print(
                    f"[VOTING] Invalid team {team} for match {match_name} (teams: {match['team1']}, {match['team2']})"
                )
                return False

            # Fetch groups for the participant
            cur.execute(
                "SELECT group_id FROM group_participants WHERE participant_id = %s",
                (participant_id, ))
            group_ids = [row["group_id"] for row in cur.fetchall()]
            print(
                f"[VOTING] Group IDs for participant {participant_id}: {group_ids}"
            )

            # If this is a Power Play vote, check the limit
            if is_power_play:
                # Check the total Power Play count across all groups
                cur.execute(
                    """
                    SELECT SUM(power_play_count) as total_power_plays
                    FROM scores
                    WHERE participant_id = %s
                """, (participant_id, ))
                result = cur.fetchone()
                total_power_plays = result["total_power_plays"] if result[
                    "total_power_plays"] is not None else 0
                print(
                    f"[VOTING] Total Power Plays used by participant_id={participant_id}: {total_power_plays}"
                )

                # Enforce the Power Play limit (e.g., 5 Power Plays per user)
                POWER_PLAY_LIMIT = 5
                if total_power_plays >= POWER_PLAY_LIMIT:
                    print(
                        f"[VOTING] Power Play limit reached for participant_id={participant_id} (limit: {POWER_PLAY_LIMIT})"
                    )
                    return False  # Indicate that the Power Play cannot be used

            print(
                f"[VOTING] Recording vote: participant_id={participant_id}, match_id={match['id']}, match_name={match_name}, team={team}, is_power_play={is_power_play}"
            )

            # Check if this is a vote change (i.e., an existing vote exists)
            is_vote_change = False
            for group_id in group_ids:
                cur.execute(
                    """
                    SELECT is_power_play
                    FROM votes
                    WHERE match_id = %s AND participant_id = %s AND group_id = %s
                """, (match["id"], participant_id, group_id))
                existing_vote = cur.fetchone()
                if existing_vote:
                    is_vote_change = True
                    break

            # Record vote for each group
            for group_id in group_ids:
                cur.execute(
                    """
                    INSERT INTO votes (match_id, participant_id, group_id, team, is_power_play)
                    VALUES (%s, %s, %s, %s, %s) ON CONFLICT (match_id, participant_id, group_id) DO UPDATE
                    SET team = EXCLUDED.team, is_power_play = EXCLUDED.is_power_play
                """, (match["id"], participant_id, group_id, team,
                      is_power_play))
                print(
                    f"[VOTING] Vote recorded/updated: participant_id={participant_id}, match_id={match['id']}, group_id={group_id}, team={team}, is_power_play={is_power_play}"
                )

                # If this is a new Power Play vote (not a change to an existing Power Play vote), increment the power_play_count
                if is_power_play and not (is_vote_change
                                          and existing_vote["is_power_play"]):
                    # Ensure the scores entry exists
                    cur.execute(
                        """
                        INSERT INTO scores (participant_id, group_id, score, power_play_count, win_streak, loss_streak)
                        VALUES (%s, %s, 0, 0, 0, 0)
                        ON CONFLICT (participant_id, group_id) DO NOTHING
                    """, (participant_id, group_id))
                    # Increment the power_play_count
                    cur.execute(
                        """
                        UPDATE scores
                        SET power_play_count = power_play_count + 1
                        WHERE participant_id = %s AND group_id = %s
                    """, (participant_id, group_id))
                    print(
                        f"[VOTING] Incremented power_play_count for participant_id={participant_id}, group_id={group_id}"
                    )

            conn.commit()
            print(
                f"[VOTING] Vote recording completed for participant_id={participant_id}, match_name={match_name}"
            )
            return True
