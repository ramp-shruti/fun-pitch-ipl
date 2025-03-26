def update_scores(match_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get the winner of the match
            cur.execute("SELECT winner FROM results WHERE match_id = %s",
                        (match_id, ))
            winner = cur.fetchone()["winner"]

            # Get all groups that have votes for this match
            cur.execute(
                "SELECT DISTINCT group_id FROM votes WHERE match_id = %s",
                (match_id, ))
            group_ids = [row["group_id"] for row in cur.fetchall()]

            # Process each group
            for group_id in group_ids:
                # Get votes for this match and group, only for active participants
                cur.execute(
                    """
                    SELECT v.participant_id, v.team, v.is_power_play
                    FROM votes v
                    JOIN active_participants ap ON v.participant_id = ap.participant_id
                    WHERE v.match_id = %s AND v.group_id = %s
                """, (match_id, group_id))
                votes = cur.fetchall()

                # Calculate the losers' pool
                losers_pool = sum(20 if v["is_power_play"] else 10
                                  for v in votes if v["team"] != winner)

                # Identify winners
                winners = [v for v in votes if v["team"] == winner]

                # Calculate total winner bets
                total_winner_bets = sum(20 if v["is_power_play"] else 10
                                        for v in winners) if winners else 0

                # Distribute points to winners proportionally, ensuring the entire pool is used
                if winners and total_winner_bets > 0:
                    remaining_pool = losers_pool
                    winner_points = []
                    for i, winner in enumerate(winners):
                        winner_bet = 20 if winner["is_power_play"] else 10
                        # Calculate points for this winner
                        if i == len(
                                winners
                        ) - 1:  # Last winner gets the remaining pool to avoid rounding issues
                            points = remaining_pool
                        else:
                            points = (losers_pool *
                                      winner_bet) // total_winner_bets
                            remaining_pool -= points
                        winner_points.append(
                            (winner["participant_id"], points))
                else:
                    winner_points = []

                # Update scores for each participant
                for vote in votes:
                    participant_id = vote["participant_id"]
                    is_power_play = vote["is_power_play"]
                    if vote["team"] == winner:
                        # Find the points for this winner
                        points = next(points for pid, points in winner_points
                                      if pid == participant_id)
                        cur.execute(
                            """
                            UPDATE scores SET score = score + %s, win_streak = win_streak + 1, loss_streak = 0
                            WHERE participant_id = %s AND group_id = %s
                        """, (points, participant_id, group_id))
                    else:
                        points = -20 if is_power_play else -10
                        cur.execute(
                            """
                            UPDATE scores SET score = score + %s, loss_streak = loss_streak + 1, win_streak = 0
                            WHERE participant_id = %s AND group_id = %s
                        """, (points, participant_id, group_id))
                conn.commit()
