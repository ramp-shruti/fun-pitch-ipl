# results.py
from database import get_db_connection
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import threading
import time


def update_scores(match_id, match_name, winner):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch all votes for the match
            cur.execute(
                """
                SELECT v.participant_id, v.group_id, v.team, v.is_power_play, p.name
                FROM votes v
                JOIN participants p ON v.participant_id = p.id
                WHERE v.match_id = %s
            """, (match_id, ))
            votes = cur.fetchall()
            print(
                f"[RESULTS] Votes for match_id={match_id}: {[(v['participant_id'], v['group_id'], v['team'], v['is_power_play']) for v in votes]}"
            )

            # Process scores for each group
            cur.execute("SELECT id FROM groups")
            group_ids = [row["id"] for row in cur.fetchall()]
            for group_id in group_ids:
                group_votes = [v for v in votes if v["group_id"] == group_id]
                if not group_votes:
                    continue

                # Separate winners and losers
                winners = [v for v in group_votes if v["team"] == winner]
                losers = [v for v in group_votes if v["team"] != winner]
                print(
                    f"[RESULTS] Group {group_id} - Winners: {[(w['participant_id'], w['name']) for w in winners]}, Losers: {[(l['participant_id'], l['name']) for l in losers]}"
                )

                # If there are no losers, winners get 0 points (zero-sum)
                if not losers:
                    for participant in group_votes:
                        participant_id = participant["participant_id"]
                        # Update scores (no points awarded)
                        cur.execute(
                            """
                            INSERT INTO scores (participant_id, group_id, score, power_play_count, win_streak, loss_streak)
                            VALUES (%s, %s, 0, 0, 0, 0)
                            ON CONFLICT (participant_id, group_id)
                            DO UPDATE SET win_streak = GREATEST(scores.win_streak + 1, 0),
                                          loss_streak = 0
                        """, (participant_id, group_id))
                        print(
                            f"[RESULTS] No losers in group_id={group_id}, participant_id={participant_id} gets 0 points"
                        )
                    continue

                # If there are no winners, losers lose points but no redistribution
                if not winners:
                    for participant in group_votes:
                        participant_id = participant["participant_id"]
                        is_power_play = participant["is_power_play"]
                        base_points = 20 if is_power_play else 10
                        points = -base_points  # Losers lose points
                        cur.execute(
                            """
                            INSERT INTO scores (participant_id, group_id, score, power_play_count, win_streak, loss_streak)
                            VALUES (%s, %s, %s, 0, 0, 0)
                            ON CONFLICT (participant_id, group_id)
                            DO UPDATE SET score = scores.score + %s,
                                          win_streak = 0,
                                          loss_streak = GREATEST(scores.loss_streak + 1, 0)
                        """, (participant_id, group_id, points, points))
                        print(
                            f"[RESULTS] No winners in group_id={group_id}, participant_id={participant_id} loses {points} points"
                        )
                    continue

                # Calculate total points to redistribute
                total_points = sum(20 if v["is_power_play"] else 10
                                   for v in group_votes)
                total_winner_points = sum(20 if w["is_power_play"] else 10
                                          for w in winners)
                total_loser_points = sum(20 if l["is_power_play"] else 10
                                         for l in losers)
                print(
                    f"[RESULTS] Group {group_id} - Total points: {total_points}, Total winner points: {total_winner_points}, Total loser points: {total_loser_points}"
                )

                # Redistribute points to ensure zero-sum
                for participant in group_votes:
                    participant_id = participant["participant_id"]
                    is_power_play = participant["is_power_play"]
                    base_points = 20 if is_power_play else 10
                    if participant["team"] == winner:
                        # Winners gain points proportional to their contribution
                        points = (base_points /
                                  total_winner_points) * total_loser_points
                        points = round(points)  # Round to nearest integer
                        cur.execute(
                            """
                            INSERT INTO scores (participant_id, group_id, score, power_play_count, win_streak, loss_streak)
                            VALUES (%s, %s, %s, 0, 0, 0)
                            ON CONFLICT (participant_id, group_id)
                            DO UPDATE SET score = scores.score + %s,
                                          win_streak = GREATEST(scores.win_streak + 1, 0),
                                          loss_streak = 0
                        """, (participant_id, group_id, points, points))
                        print(
                            f"[RESULTS] Winner participant_id={participant_id} in group_id={group_id} gains {points} points"
                        )
                    else:
                        # Losers lose points proportional to their contribution
                        points = -base_points
                        cur.execute(
                            """
                            INSERT INTO scores (participant_id, group_id, score, power_play_count, win_streak, loss_streak)
                            VALUES (%s, %s, %s, 0, 0, 0)
                            ON CONFLICT (participant_id, group_id)
                            DO UPDATE SET score = scores.score + %s,
                                          win_streak = 0,
                                          loss_streak = GREATEST(scores.loss_streak + 1, 0)
                        """, (participant_id, group_id, points, points))
                        print(
                            f"[RESULTS] Loser participant_id={participant_id} in group_id={group_id} loses {points} points"
                        )

            conn.commit()
            print(f"[RESULTS] Scores updated for match_name={match_name}")


def check_and_update_results(cricapi_key):
    while True:
        now = datetime.now(ZoneInfo("UTC"))
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Find matches that have ended but don't have results yet
                cur.execute(
                    """
                    SELECT id, match_name, cricapi_id
                    FROM matches
                    WHERE match_time + INTERVAL '3 hours 30 minutes' < %s
                    AND id NOT IN (SELECT match_id FROM results)
                """, (now, ))
                ended_matches = cur.fetchall()
                print(
                    f"[RESULTS] Ended matches without results: {[(m['id'], m['match_name']) for m in ended_matches]}"
                )

                for match in ended_matches:
                    match_id = match["id"]
                    match_name = match["match_name"]
                    cricapi_id = match["cricapi_id"]

                    # Fetch match result from CricAPI
                    match_info_url = f"https://api.cricapi.com/v1/match_info?apikey={cricapi_key}&id={cricapi_id}"
                    try:
                        response = requests.get(match_info_url)
                        response.raise_for_status()
                        match_data = response.json()
                        print(
                            f"[RESULTS] CricAPI response for match_id={match_id}: {match_data}"
                        )

                        if "data" in match_data and match_data["data"][
                                "matchEnded"]:
                            winner = None
                            if "score" in match_data["data"]:
                                scores = match_data["data"]["score"]
                                if len(scores) >= 2:  # Assuming two innings
                                    team1_score = scores[0]["r"]
                                    team2_score = scores[1]["r"]
                                    team1 = match_data["data"]["teams"][0]
                                    team2 = match_data["data"]["teams"][1]
                                    if team1_score > team2_score:
                                        winner = team1
                                    elif team2_score > team1_score:
                                        winner = team2
                                    print(
                                        f"[RESULTS] Determined winner for match_id={match_id}: {winner}"
                                    )

                            if winner:
                                # Insert result into the database
                                cur.execute(
                                    """
                                    INSERT INTO results (match_id, winner)
                                    VALUES (%s, %s)
                                """, (match_id, winner))
                                conn.commit()
                                print(
                                    f"[RESULTS] Result recorded for match_id={match_id}: Winner={winner}"
                                )

                                # Update scores
                                update_scores(match_id, match_name, winner)
                    except requests.exceptions.RequestException as e:
                        print(
                            f"[RESULTS] Error fetching result for match_id={match_id}: {e}"
                        )

        time.sleep(300)  # Check every 5 minutes


def start_results_thread(cricapi_key):
    print("[RESULTS] Starting results thread...")
    thread = threading.Thread(target=check_and_update_results,
                              args=(cricapi_key, ))
    thread.daemon = True
    thread.start()
    print("[RESULTS] Results thread started")
