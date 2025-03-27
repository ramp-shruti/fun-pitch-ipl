# app.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from database import get_db_connection, insert_participant, link_participant_to_group, fetch_existing_id, activate_participant, get_vote_context, clear_vote_context, set_vote_context
from voting import record_vote
from messaging import send_vote_prompt, send_message
from results import start_results_thread
import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

app = Flask(__name__)
cricapi_key = os.environ.get('CRICAPI_KEY')

potential_participants_data = {
    "whatsapp:+919810272993": {
        "name": "Ram",
        "groups": ["gg", "caricket"]
    },
    "whatsapp:+919910604809": {
        "name": "Nataraj",
        "groups": ["gg"]
    },
    "whatsapp:+16693179207": {
        "name": "Alok",
        "groups": ["gg", "caricket"]
    },
    "whatsapp:+919810070837": {
        "name": "Ashish",
        "groups": ["gg", "caricket"]
    },
    "whatsapp:+919873009705": {
        "name": "Anmol",
        "groups": ["gg", "caricket"]
    },
    "whatsapp:+919350645483": {
        "name": "Akshat",
        "groups": ["caricket"]
    },
    "whatsapp:+919891368846": {
        "name": "Akshaya",
        "groups": ["caricket"]
    },
    "whatsapp:+919810804696": {
        "name": "Ankit",
        "groups": ["caricket"]
    },
    "whatsapp:+919810732204": {
        "name": "Basu",
        "groups": ["caricket"]
    },
    "whatsapp:+919810688085": {
        "name": "Mansukh",
        "groups": ["caricket"]
    },
    "whatsapp:+919810295191": {
        "name": "Rahul",
        "groups": ["caricket"]
    },
    "whatsapp:+919810842455": {
        "name": "Rajesh",
        "groups": ["caricket"]
    },
    "whatsapp:+14152693271": {
        "name": "Sachin",
        "groups": ["caricket"]
    },
    "whatsapp:+918800684252": {
        "name": "Sameer",
        "groups": ["caricket"]
    },
    "whatsapp:+919871115644": {
        "name": "Satish",
        "groups": ["caricket"]
    },
    "whatsapp:+919871291961": {
        "name": "Saurabh",
        "groups": ["caricket"]
    },
    "whatsapp:+919811321562": {
        "name": "Srijan",
        "groups": ["caricket"]
    },
    "whatsapp:+16506468145": {
        "name": "Swapnil",
        "groups": ["caricket"]
    },
    "whatsapp:+919818556094": {
        "name": "Dheeraj",
        "groups": ["caricket"]
    }
}

team_acronyms = {
    "Chennai Super Kings": "CSK",
    "Mumbai Indians": "MI",
    "Royal Challengers Bengaluru": "RCB",
    "Kolkata Knight Riders": "KKR",
    "Sunrisers Hyderabad": "SRH",
    "Rajasthan Royals": "RR",
    "Punjab Kings": "PBKS",
    "Delhi Capitals": "DC",
    "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG"
}


def send_action_menu(participant, participant_id):
    now = datetime.now(ZoneInfo("UTC"))
    print(
        f"[APP] Sending action menu to participant_id={participant_id}, phone={participant}"
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check for a live match (between start time and start time + 3h30m)
            cur.execute(
                """
                SELECT match_name, team1, team2, match_time
                FROM matches
                WHERE match_time <= %s
                AND match_time + INTERVAL '3 hours 30 minutes' >= %s
                ORDER BY match_time LIMIT 1
            """, (now, now))
            live_match = cur.fetchone()
            print(f"[APP] Live match check: {live_match}")

            # Check for the next upcoming match to determine if the user can change their vote
            cur.execute(
                """
                SELECT match_name, team1, team2
                FROM matches
                WHERE match_time > %s
                ORDER BY match_time LIMIT 1
            """, (now, ))
            next_match = cur.fetchone()
            print(f"[APP] Next upcoming match: {next_match}")

            # Base action menu
            message_body = "🏏 **Caricket Actions**\n\n"

            # General Actions
            available_options = []

            if live_match:
                team1, team2 = live_match["team1"], live_match["team2"]
                team1_short, team2_short = team_acronyms[team1], team_acronyms[
                    team2]
                message_body += f"🔹 L️ **Live** ({team1_short} vs {team2_short}) 📡\n"
                available_options.append("L")

            message_body += "🔹 V️ **Vote** 🏆\n"
            message_body += "🔹 M️ **My Votes** 🗳️\n"
            message_body += "🔹 P️ **Points** 🚀\n\n"
            available_options.extend(["V", "M", "P"])

            # Upcoming Match Actions
            if next_match:
                match_name = next_match["match_name"]
                team1, team2 = next_match["team1"], next_match["team2"]
                team1_short, team2_short = team_acronyms[team1], team_acronyms[
                    team2]

                message_body += f"**Upcoming [{team1_short} vs {team2_short}]**\n"
                message_body += "🔹 W️ **Who's Where** 📊\n"
                available_options.append("W")

                cur.execute(
                    """
                    SELECT team, is_power_play
                    FROM votes
                    WHERE match_id = (SELECT id FROM matches WHERE match_name = %s)
                    AND participant_id = %s
                    LIMIT 1
                """, (match_name, participant_id))
                existing_vote = cur.fetchone()
                print(
                    f"[APP] Checking if participant_id={participant_id} has voted for match_name={match_name}: {existing_vote}"
                )

                if existing_vote:
                    message_body += "🔹 C️ **Change my pick** 🔄\n"
                    available_options.append("C")

            # Instructions
            options_str = ", ".join(f"*{opt}*" for opt in available_options)
            message_body += f"\n💬 Reply {options_str} to choose!"

            send_message(participant, message_body)


def handle_unrecognized_message(sender, message, participant_id):
    name = potential_participants_data[sender]["name"]
    now = datetime.now(ZoneInfo("UTC"))
    print(
        f"[APP] Handling unrecognized message from sender={sender}, message={message}, participant_id={participant_id}"
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check for a live match
            cur.execute(
                """
                SELECT match_name
                FROM matches
                WHERE match_time <= %s
                AND match_time + INTERVAL '3 hours 30 minutes' >= %s
                ORDER BY match_time LIMIT 1
            """, (now, now))
            live_match = cur.fetchone()
            print(
                f"[APP] Live match check for unrecognized message: {live_match}"
            )

            # Check if the user has voted for the next upcoming match
            cur.execute(
                """
                SELECT match_name
                FROM matches
                WHERE match_time > %s
                ORDER BY match_time LIMIT 1
            """, (now, ))
            next_match = cur.fetchone()
            print(
                f"[APP] Next upcoming match for unrecognized message: {next_match}"
            )

            has_voted = False
            if next_match:
                match_name = next_match["match_name"]
                cur.execute(
                    """
                    SELECT team
                    FROM votes
                    WHERE match_id = (SELECT id FROM matches WHERE match_name = %s)
                    AND participant_id = %s
                    LIMIT 1
                """, (match_name, participant_id))
                if cur.fetchone():
                    has_voted = True
                print(
                    f"[APP] Has voted for next match ({match_name}): {has_voted}"
                )

            if live_match and has_voted:
                return (
                    f"Sorry {name}, I didn’t catch that! 😅 Reply with *L*, *V*, *M*, *P*, *W*, or *C* to choose!"
                )
            elif live_match:
                return (
                    f"Sorry {name}, I didn’t catch that! 😅 Reply with *L*, *V*, *M*, *P*, or *W* to choose!"
                )
            elif has_voted:
                return (
                    f"Sorry {name}, I didn’t catch that! 😅 Reply with *V*, *M*, *P*, *W*, or *C* to choose!"
                )
            else:
                return (
                    f"Sorry {name}, I didn’t catch that! 😅 Reply with *V*, *M*, *P*, or *W* to choose!"
                )


def show_current_votes(participant, participant_id):
    now = datetime.now(ZoneInfo("UTC"))
    print(
        f"[APP] Showing current votes for participant_id={participant_id}, phone={participant}"
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT match_name, team1, team2
                FROM matches
                WHERE match_time > %s
                ORDER BY match_time LIMIT 1
            """, (now, ))
            current_match = cur.fetchone()
            print(f"[APP] Current match for votes: {current_match}")
            if not current_match:
                name = potential_participants_data[participant]["name"]
                send_message(
                    participant,
                    f"No upcoming matches to show votes for, {name}! Wait for the next one..."
                )
                send_action_menu(participant, participant_id)
                return

            match_name = current_match["match_name"]
            team1, team2 = current_match["team1"], current_match["team2"]
            team1_short, team2_short = team_acronyms[team1], team_acronyms[
                team2]

            cur.execute(
                "SELECT g.id, g.name FROM groups g JOIN group_participants gp ON g.id = gp.group_id WHERE gp.participant_id = %s",
                (participant_id, ))
            sender_groups = cur.fetchall()
            print(
                f"[APP] Sender groups for participant_id={participant_id}: {[(g['id'], g['name']) for g in sender_groups]}"
            )

            message = ""
            for group in sender_groups:
                group_id = group["id"]
                group_name = group["name"]
                message += f"🏏 **{match_name}: {team1_short} 🆚 {team2_short}** ({group_name})\n\n🗳️ **Who’s Where?**\n"

                cur.execute(
                    """
                    SELECT p.id, p.name
                    FROM participants p
                    JOIN group_participants gp ON p.id = gp.participant_id
                    JOIN groups g ON gp.group_id = g.id
                    WHERE g.id = %s
                """, (group_id, ))
                group_participants = cur.fetchall()
                print(
                    f"[APP] Group participants for group_id={group_id}: {[(p['id'], p['name']) for p in group_participants]}"
                )

                for p in group_participants:
                    p_id = p["id"]
                    p_name = p["name"]
                    cur.execute(
                        """
                        SELECT team, is_power_play
                        FROM votes
                        WHERE match_id = (SELECT id FROM matches WHERE match_name = %s)
                        AND participant_id = %s
                        AND group_id = %s
                    """, (match_name, p_id, group_id))
                    vote = cur.fetchone()
                    if vote:
                        team = vote["team"]
                        is_power_play = vote["is_power_play"]
                        message += f"- {p_name}: {team}{' (PP)' if is_power_play else ''}\n"
                    else:
                        message += f"- {p_name}: No vote yet\n"
                message += "\n"
            send_message(participant, message.strip())
            send_action_menu(participant, participant_id)


def show_my_votes(participant, participant_id):
    name = potential_participants_data[participant]["name"]
    print(
        f"[APP] Showing my votes for participant_id={participant_id}, phone={participant}, name={name}"
    )
    message = f"🏏 **Your Votes, {name}** (Shared across groups):\n"
    voted = False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.match_name, m.team1, m.team2, m.match_time, v.team, v.is_power_play
                FROM votes v
                JOIN matches m ON v.match_id = m.id
                WHERE v.participant_id = %s
                ORDER BY m.match_time
            """, (participant_id, ))
            votes = cur.fetchall()
            print(
                f"[APP] Votes for participant_id={participant_id}: {[(v['match_name'], v['team'], v['is_power_play']) for v in votes]}"
            )

            for vote in votes:
                match = vote["match_name"]
                team = vote["team"]
                is_power_play = vote["is_power_play"]
                match_time = vote["match_time"]
                match_time_ist = match_time + timedelta(hours=5, minutes=30)
                time_str = match_time_ist.strftime("%B %d, %I:%M %p IST")
                message += f"- {match} ({time_str}): {team}{' (PP)' if is_power_play else ''}\n"
                voted = True

    if not voted:
        message += "You haven’t cast any votes yet! 🗳️\n"
    message += "\n"
    send_message(participant, message.strip())
    send_action_menu(participant, participant_id)


def get_leaderboard_with_leader(group_id):
    print(f"[APP] Generating leaderboard for group_id={group_id}")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.name, s.score
                FROM scores s
                JOIN participants p ON s.participant_id = p.id
                WHERE s.group_id = %s
                ORDER BY s.score DESC
            """, (group_id, ))
            sorted_lb = cur.fetchall()
            print(
                f"[APP] Leaderboard for group_id={group_id}: {[(row['name'], row['score']) for row in sorted_lb]}"
            )
            if not sorted_lb:
                return "No scores yet—get voting!"
            leader_name = sorted_lb[0]["name"]
            leader_score = sorted_lb[0]["score"]
            leaderboard_str = f"**{leader_name}: {leader_score}** 🏆\n"
            for row in sorted_lb[1:]:
                name = row["name"]
                score = row["score"]
                emoji = "🟢" if score > 0 else "🔴" if score < 0 else ""
                leaderboard_str += f"{name}: {score} {emoji}\n"
            return leaderboard_str


def get_live_match_status(cricapi_id):
    print(f"[APP] Fetching live match status for cricapi_id={cricapi_id}")
    match_info_url = f"https://api.cricapi.com/v1/match_info?apikey={cricapi_key}&id={cricapi_id}"
    try:
        response = requests.get(match_info_url)
        response.raise_for_status()
        match_data = response.json()
        print(f"[APP] CricAPI response: {match_data}")

        if "data" not in match_data or "status" not in match_data["data"]:
            print(f"[APP] No status available for cricapi_id={cricapi_id}")
            return "No live status available."

        status = match_data["data"]["status"]
        message = f"{status}\n"

        if "score" in match_data["data"]:
            for score in match_data["data"]["score"]:
                inning = score["inning"]
                runs = score["r"]
                wickets = score["w"]
                overs = score["o"]
                message += f"{inning}: {runs}/{wickets} ({overs} overs)\n"

        return message.strip()
    except requests.exceptions.RequestException as e:
        print(
            f"[APP] Error fetching live match status for cricapi_id={cricapi_id}: {e}"
        )
        return "Error fetching live status."


@app.route("/")
def home():
    print("[APP] Home route accessed")
    return "Welcome to the IPL Prediction Bot! This app handles WhatsApp messages at /whatsapp."


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    sender = request.values.get("From")
    print(f"[APP] Received message: sender={sender}, message={incoming_msg}")
    resp = MessagingResponse()

    if sender not in potential_participants_data:
        print(f"[APP] Sender {sender} not in potential participants")
        send_message(
            sender,
            "You’re not a potential participant! Contact the admin to join.")
        return str(resp)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            participant_id = fetch_existing_id("participants", "phone", sender)
            if not participant_id:
                print(
                    f"[APP] Participant not found for sender={sender}, creating new participant"
                )
                participant_id = insert_participant(
                    sender, potential_participants_data[sender]["name"])
                for group_name in potential_participants_data[sender][
                        "groups"]:
                    group_id = fetch_existing_id("groups", "name", group_name)
                    link_participant_to_group(group_id, participant_id)
                activate_participant(participant_id)
                send_message(
                    sender,
                    f"Welcome to the IPL Prediction Game, {potential_participants_data[sender]['name']}!"
                )
            else:
                print(
                    f"[APP] Activating existing participant: sender={sender}, participant_id={participant_id}"
                )
                activate_participant(participant_id)

            cur.execute(
                "SELECT * FROM active_participants WHERE participant_id = %s",
                (participant_id, ))
            if not cur.fetchone():
                print(f"[APP] Participant_id={participant_id} is not active")
                send_message(
                    sender,
                    "You’re not an active participant yet. Send a message to join the game!"
                )
                return str(resp)

            cur.execute("SELECT name FROM participants WHERE phone = %s",
                        (sender, ))
            participant = cur.fetchone()
            name = participant["name"]
            print(
                f"[APP] Participant details: phone={sender}, participant_id={participant_id}, name={name}"
            )

            cur.execute(
                "SELECT g.id, g.name FROM groups g JOIN group_participants gp ON g.id = gp.group_id WHERE gp.participant_id = %s",
                (participant_id, ))
            sender_groups = cur.fetchall()
            print(
                f"[APP] Sender groups for participant_id={participant_id}: {[(g['id'], g['name']) for g in sender_groups]}"
            )

            if incoming_msg == "hi":
                send_action_menu(sender, participant_id)
            elif incoming_msg == "v":
                now = datetime.now(ZoneInfo("UTC"))
                print(
                    f"[APP] Handling 'v' command: Finding next unvoted match for participant_id={participant_id}"
                )
                cur.execute(
                    """
                    SELECT match_name FROM matches
                    WHERE match_time > %s
                    AND id NOT IN (
                        SELECT match_id FROM votes v 
                        WHERE v.participant_id = %s
                        AND v.match_id IN (SELECT id FROM matches WHERE match_time > %s)
                        GROUP BY match_id
                        HAVING COUNT(*) >= (SELECT COUNT(*) FROM group_participants gp WHERE gp.participant_id = %s)
                    )
                    ORDER BY match_time LIMIT 1
                """, (now, participant_id, now, participant_id))
                match = cur.fetchone()
                print(
                    f"[APP] Next unvoted match for participant_id={participant_id}: {match}"
                )
                if match:
                    send_vote_prompt(sender, match["match_name"], conn,
                                     participant_id)
                else:
                    send_message(sender, f"All matches voted, {name}!")
                    send_action_menu(sender, participant_id)
            elif incoming_msg == "c":
                now = datetime.now(ZoneInfo("UTC"))
                print(
                    f"[APP] Handling 'c' command: Finding next match to change vote for participant_id={participant_id}"
                )
                cur.execute(
                    """
                    SELECT match_name, team1, team2, match_time
                    FROM matches
                    WHERE match_time > %s
                    ORDER BY match_time LIMIT 1
                """, (now, ))
                match = cur.fetchone()
                print(f"[APP] Next match for change: {match}")
                if not match:
                    send_message(
                        sender,
                        f"No upcoming matches to change votes for, {name}!")
                    send_action_menu(sender, participant_id)
                    return

                match_name = match["match_name"]
                match_time = match["match_time"]
                team1, team2 = match["team1"], match["team2"]
                team1_short, team2_short = team_acronyms[team1], team_acronyms[
                    team2]

                cur.execute(
                    """
                    SELECT team, is_power_play
                    FROM votes
                    WHERE match_id = (SELECT id FROM matches WHERE match_name = %s)
                    AND participant_id = %s
                    LIMIT 1
                """, (match_name, participant_id))
                existing_vote = cur.fetchone()
                print(
                    f"[APP] Existing vote for match_name={match_name}, participant_id={participant_id}: {existing_vote}"
                )

                if existing_vote:
                    team = existing_vote["team"]
                    is_power_play = existing_vote["is_power_play"]
                    message = (
                        f"You’ve voted for **{team}**{' (PP)' if is_power_play else ''} in **{match_name}: {team1_short} 🆚 {team2_short}**!\n\n"
                        f"Change your vote:\n"
                        f"Reply *'1'* for **{team1_short}**\n"
                        f"Reply *'2'* for **{team2_short}**\n"
                        f"Reply *'PP 1'* or *'PP 2'* to use a Power Play!\n"
                        f"⏳ **Vote before:** {match_time.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%I:%M %p IST on %B %d, %Y')}!"
                    )
                    # Store the match name in vote_context for the change
                    set_vote_context(participant_id, match_name)
                    print(
                        f"[APP] Set vote context for change: participant_id={participant_id}, match_name={match_name}"
                    )
                    send_message(sender, message)
                else:
                    send_message(
                        sender,
                        f"You haven’t voted for {match_name} yet, {name}! Use *V* to vote first."
                    )
                    send_action_menu(sender, participant_id)
            elif incoming_msg in ("1", "2", "pp 1", "pp 2"):
                now = datetime.now(ZoneInfo("UTC"))
                print(
                    f"[APP] Handling vote input: incoming_msg={incoming_msg}, sender={sender}, participant_id={participant_id}"
                )

                # Get the match name from vote_context
                match_name = get_vote_context(participant_id)
                print(
                    f"[APP] Retrieved vote context for participant_id={participant_id}: match_name={match_name}"
                )
                if not match_name:
                    print(
                        f"[APP] No vote context found for participant_id={participant_id}, prompting to use V or C"
                    )
                    send_message(
                        sender,
                        f"Please use *V* to vote for a new match or *C* to change your vote, {name}!"
                    )
                    send_action_menu(sender, participant_id)
                    return

                # Fetch match details using the match name from context
                cur.execute(
                    """
                    SELECT match_name, team1, team2, match_time
                    FROM matches
                    WHERE match_name = %s
                """, (match_name, ))
                match = cur.fetchone()
                print(f"[APP] Match details from context: {match}")
                if not match:
                    print(f"[APP] Match not found for match_name={match_name}")
                    send_message(
                        sender,
                        f"Invalid match context, {name}! Please use *V* to vote again."
                    )
                    clear_vote_context(participant_id)
                    send_action_menu(sender, participant_id)
                    return

                match_time = match["match_time"]
                if now > match_time:
                    print(
                        f"[APP] Match {match_name} has started at {match_time}, voting not allowed"
                    )
                    send_message(
                        sender,
                        f"Oops, {name}, {match_name} has started—too late to vote or change your vote!"
                    )
                    clear_vote_context(participant_id)
                    send_action_menu(sender, participant_id)
                    return

                team = match["team1"] if "1" in incoming_msg else match["team2"]
                is_power_play = incoming_msg.startswith("pp")
                print(
                    f"[APP] Recording vote for team: {team}, is_power_play: {is_power_play}, match_name: {match_name}, participant_id: {participant_id}"
                )

                # Check if this is a vote change
                cur.execute(
                    """
                    SELECT team, is_power_play
                    FROM votes
                    WHERE match_id = (SELECT id FROM matches WHERE match_name = %s)
                    AND participant_id = %s
                    LIMIT 1
                """, (match_name, participant_id))
                existing_vote = cur.fetchone()
                is_vote_change = existing_vote is not None
                print(
                    f"[APP] Is vote change: {is_vote_change}, existing vote: {existing_vote}"
                )

                if record_vote(sender, match_name, team, is_power_play):
                    # Confirm the vote was recorded correctly by querying the votes table
                    cur.execute(
                        """
                        SELECT team, is_power_play
                        FROM votes
                        WHERE match_id = (SELECT id FROM matches WHERE match_name = %s)
                        AND participant_id = %s
                    """, (match_name, participant_id))
                    recorded_votes = cur.fetchall()
                    print(
                        f"[APP] Recorded votes in database for match_name={match_name}, participant_id={participant_id}: {[(v['team'], v['is_power_play']) for v in recorded_votes]}"
                    )

                    # Send appropriate message
                    if is_vote_change:
                        send_message(
                            sender,
                            f"Vote changed to {team}{' (PP)' if is_power_play else ''} for {match_name}, {name}!"
                        )
                    else:
                        send_message(
                            sender,
                            f"Vote recorded for {team}{' (PP)' if is_power_play else ''}, {name}!"
                        )

                    # Clear the vote context
                    clear_vote_context(participant_id)
                    print(
                        f"[APP] Cleared vote context for participant_id={participant_id}"
                    )

                    # Find the next unvoted match
                    cur.execute(
                        """
                        SELECT match_name FROM matches
                        WHERE match_time > %s
                        AND id NOT IN (
                            SELECT match_id FROM votes v 
                            WHERE v.participant_id = %s
                            AND v.match_id IN (SELECT id FROM matches WHERE match_time > %s)
                            GROUP BY match_id
                            HAVING COUNT(*) >= (SELECT COUNT(*) FROM group_participants gp WHERE gp.participant_id = %s)
                        )
                        ORDER BY match_time LIMIT 1
                    """, (now, participant_id, now, participant_id))
                    next_match = cur.fetchone()
                    print(
                        f"[APP] Next match after voting for participant_id={participant_id}: {next_match}"
                    )
                    if next_match:
                        send_vote_prompt(sender, next_match["match_name"],
                                         conn, participant_id)
                    else:
                        send_message(sender,
                                     f"Nice one, {name}! All matches voted!")
                        send_action_menu(sender, participant_id)
                else:
                    print(
                        f"[APP] Failed to record vote for match_name={match_name}, team={team}, is_power_play={is_power_play}"
                    )
                    send_message(sender, "Invalid vote or match started!")
                    clear_vote_context(participant_id)
                    send_action_menu(sender, participant_id)
            elif incoming_msg == "l":
                now = datetime.now(ZoneInfo("UTC"))
                print(f"[APP] Handling 'l' command: Finding live match")
                cur.execute(
                    """
                    SELECT match_name, team1, team2, cricapi_id
                    FROM matches
                    WHERE match_time <= %s
                    AND match_time + INTERVAL '3 hours 30 minutes' >= %s
                    ORDER BY match_time LIMIT 1
                """, (now, now))
                live_match = cur.fetchone()
                print(f"[APP] Live match: {live_match}")
                if not live_match:
                    send_message(sender,
                                 f"No match is currently live, {name}!")
                    send_action_menu(sender, participant_id)
                    return

                match_name = live_match["match_name"]
                team1, team2 = live_match["team1"], live_match["team2"]
                team1_short, team2_short = team_acronyms[team1], team_acronyms[
                    team2]
                cricapi_id = live_match["cricapi_id"]

                # Fetch live status
                status = get_live_match_status(cricapi_id)
                message = (
                    f"🏏 **Live Status of {team1_short} vs {team2_short}**\n\n"
                    f"{status}")
                send_message(sender, message)
                send_action_menu(sender, participant_id)
            elif incoming_msg == "w":
                show_current_votes(sender, participant_id)
            elif incoming_msg == "p":
                print(
                    f"[APP] Handling 'p' command: Generating points table for participant_id={participant_id}"
                )
                message = ""
                for group in sender_groups:
                    group_id = group["id"]
                    group_name = group["name"]
                    message += f"Points Table ({group_name}):\n{get_leaderboard_with_leader(group_id)}\n\n"
                send_message(sender, message.strip())
                send_action_menu(sender, participant_id)
            elif incoming_msg == "m":
                show_my_votes(sender, participant_id)
            else:
                response = handle_unrecognized_message(sender, incoming_msg,
                                                       participant_id)
                send_message(sender, response)
                send_action_menu(sender, participant_id)

    return str(resp)


if __name__ == "__main__":
    print("[APP] Starting Flask app...")
    start_results_thread(cricapi_key)
    app.run(host="0.0.0.0", port=8080)
