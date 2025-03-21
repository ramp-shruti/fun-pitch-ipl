from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import datetime
import os
import threading
import time
import requests
import random

app = Flask(__name__)

# Twilio credentials from secrets
account_sid = os.environ['ACCOUNT_SID']
auth_token = os.environ['AUTH_TOKEN']
client = Client(account_sid, auth_token)

# CricAPI key from secrets
cricapi_key = os.environ['CRICAPI_KEY']

# Match details (Mock Match 1 for today)
match_schedule = {
    "Match 1": {
        "time": "2025-03-20 14:00:00",
        "teams": ("KKR", "RCB"),
        "venue": "Eden Gardens, Kolkata",
        "cricapi_id": None
    },
}

# Data storage for one group (Gossip-Group: gg)
predictions = {"gg": {}}
leaderboard = {"gg": {}}
results = {}
subscribed_players = {"gg": set()}
pending_votes = {"gg": {}}
power_play_count = {"gg": {}}
win_streaks = {"gg": {}}
loss_streaks = {"gg": {}}

# Participants for Gossip-Group (gg) - Only Ram and Garima for testing
participants = {
    "whatsapp:+919810272993": {
        "name": "Ram",
        "groups": ["gg"]
    },  # Ram
    "whatsapp:+919818876663": {
        "name": "Garima",
        "groups": ["gg"]
    }  # Garima
}

# Conversation SIDs for each group
conversation_sids = {"gg": None}

# Trash talk options
trash_talk = [
    "{winner} says: 'Better luck next time, {loser}!'",
    "{winner} to {loser}: 'Did you even watch the game?'",
    "{winner} laughs: '{loser}, your team’s still warming up!'",
    "{winner} taunts: '{loser}, stick to cheering, not picking!'"
]


# Create a Conversation for a group
def create_conversation_for_group(group):
    try:
        service_sid = os.environ.get('CONVERSATIONS_SERVICE_SID')
        if not service_sid:
            print("Warning: CONVERSATIONS_SERVICE_SID not set")
            return None
        conversation = client.conversations.services(
            service_sid).conversations.create(friendly_name=f"Caricket-{group}",
                                              attributes='{"group": "' + group +
                                              '"}')
        return conversation.sid
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None


# Add a participant to a Conversation
def add_participant_to_conversation(group, participant):
    conversation_sid = conversation_sids[group]
    client.conversations.services(
        os.environ['CONVERSATIONS_SERVICE_SID']).conversations(
            conversation_sid).participants.create(
                identity=participant, messaging_binding_address=participant)


# Initialize Conversations at startup
conversation_sids["gg"] = create_conversation_for_group("gg")
print(f"Created Conversation for gg: {conversation_sids['gg']}")


def send_morning_message():
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        today_matches = sorted(
            [(match, details) for match, details in match_schedule.items()
             if datetime.datetime.strptime(
                 details["time"], "%Y-%m-%d %H:%M:%S").replace(
                     tzinfo=datetime.timezone.utc).date() == today],
            key=lambda x: x[1]["time"])

        # Mock 7:00 AM IST (1:30 AM UTC) to run now
        if today_matches and now.minute == now.minute:  # Mock trigger
            group = "gg"  # Only Gossip-Group
            for participant in participants:
                if group in participants[participant]["groups"]:
                    name = participants[participant]["name"]
                    match, details = today_matches[0]
                    team1, team2 = details["teams"]
                    venue = details["venue"]
                    cutoff_time = datetime.datetime.strptime(
                        details["time"], "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=datetime.timezone.utc) - datetime.timedelta(
                                hours=1)
                    cutoff_str = (cutoff_time + datetime.timedelta(
                        hours=5, minutes=30)).strftime("%I:%M %p IST")
                    message = f"Good morning, {name}! First match today: {team1} vs {team2} at {venue}. Reply ‘1’ for {team1} or ‘2’ for {team2}. Power Play it with ‘PP 1’ or ‘PP 2’ (once every 5 matches)! Cutoff: {cutoff_str}!"
                    client.messages.create(body=message,
                                           from_="whatsapp:+919818609093",
                                           to=participant)
                    if (match, participant) not in predictions[group]:
                        pending_votes[group][(match, participant)] = None
        time.sleep(60)


def check_cutoffs():
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        for match, details in match_schedule.items():
            match_time = datetime.datetime.strptime(
                details["time"],
                "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            cutoff_time = match_time - datetime.timedelta(hours=1)
            if match_time.date() == today and cutoff_time <= now < match_time:
                team1, team2 = details["teams"]
                group = "gg"  # Only Gossip-Group
                message = f"Cutoff for {match}! Locked in ({group}):\n"
                power_plays = []
                for participant in participants:
                    if group in participants[participant]["groups"]:
                        name = participants[participant]["name"]
                        if (match, participant) in predictions[group]:
                            team = predictions[group][(match,
                                                       participant)].replace(
                                                           "PP ", "")
                            is_power_play = predictions[group][(
                                match, participant)].startswith("PP")
                            message += f"- {name}: {team}{' (PP)' if is_power_play else ''}\n"
                            if is_power_play:
                                power_plays.append(
                                    f"{name} went big with Power Play on {team}!"
                                )
                        else:
                            message += f"- {name}: No vote yet\n"
                if power_plays:
                    message += "\nPower Play Shoutouts:\n" + "\n".join(
                        power_plays)
                for participant in participants:
                    if group in participants[participant]["groups"]:
                        client.messages.create(body=message,
                                               from_="whatsapp:+919818609093",
                                               to=participant)
        time.sleep(60)


def fetch_and_update_results():
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        for match, details in match_schedule.items():
            if match in results:
                continue
            match_time = datetime.datetime.strptime(
                details["time"],
                "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            match_date = match_time.date()
            if match_date == today and now > match_time + datetime.timedelta(
                    hours=3, minutes=30):
                team1, team2 = details["teams"]
                winner = get_match_result(team1, team2, match_date)
                if winner:
                    results[match] = winner
                    loser = team1 if winner == team2 else team2
                    group = "gg"  # Only Gossip-Group
                    for participant in participants:
                        if group in participants[participant]["groups"] and (
                                match, participant) not in predictions[group]:
                            predictions[group][(match, participant)] = loser
                            leaderboard[group][
                                participant] = leaderboard[group].get(
                                    participant, 0) - 10
                            loss_streaks[group][
                                participant] = loss_streaks[group].get(
                                    participant, 0) + 1
                            win_streaks[group][participant] = 0
                    update_points(match, winner, group)
                    send_personalized_messages(match, winner, group)
        time.sleep(300)


def get_match_result(team1, team2, match_date):
    # Mock result for testing
    return "KKR"  # Mock KKR wins Match 1


def send_personalized_messages(match, winner, group):
    losers_pool = 0
    winners = []
    for (m, sender), team in predictions[group].items():
        if m == match:
            if team.lower() == winner.lower():
                winners.append(sender)
            else:
                losers_pool += 10
                leaderboard[group][sender] -= 10
    points_each = losers_pool // len(winners) if winners else 0

    # Collect highlights
    streaks = [
        participants.get(p,
                         p.split(':')[1])["name"] for p in participants
        if win_streaks[group].get(p, 0) == 3
    ]
    ducks = [
        participants.get(p,
                         p.split(':')[1])["name"] for p in participants
        if loss_streaks[group].get(p, 0) == 5
    ]

    for participant in participants:
        if group in participants[participant]["groups"]:
            is_power_play = (match, participant
                             ) in predictions[group] and predictions[group][(
                                 match, participant)].startswith("PP")
            name = participants[participant]["name"]
            if (match, participant) in predictions[group]:
                team = predictions[group][(match,
                                           participant)].replace("PP ", "")
                if team.lower() == winner.lower():
                    win_streaks[group][participant] = win_streaks[group].get(
                        participant, 0) + 1
                    loss_streaks[group][participant] = 0
                    points = points_each * 2 if is_power_play else points_each
                    leaderboard[group][participant] = leaderboard[group].get(
                        participant, 0) + points
                    msg = f"Boom, {name}! {winner.upper()} smashed it in {match}—you’re up {points} pts{' with Power Play!' if is_power_play else ''}!"
                else:
                    loss_streaks[group][participant] = loss_streaks[group].get(
                        participant, 0) + 1
                    win_streaks[group][participant] = 0
                    points = -20 if is_power_play else -10
                    leaderboard[group][participant] = leaderboard[group].get(
                        participant, 0) + points
                    msg = f"Ouch, {name}, {winner.upper()} took {match}—down {abs(points)} pts{' with Power Play!' if is_power_play else ''}. Next one’s yours!"
            else:
                msg = f"Hi {name}, {winner.upper()} won {match}. You didn’t vote, so we put you on the losing side—down 10 pts!"

            # Add Trash Talk if applicable
            if winners and participant not in winners and predictions[
                    group].get((match, participant)):
                winner_name = participants.get(random.choice(winners),
                                               {"name": "a champ"})["name"]
                loser_name = name
                trash = random.choice(trash_talk).format(winner=winner_name,
                                                         loser=loser_name)
                msg += f" {trash}"

            # Add Streak Bonuses and Duck King
            streak_msg = ""
            if win_streaks[group].get(participant, 0) == 3:
                leaderboard[group][participant] += 10
                streak_msg += f"\nStreak Bonus: {name} scored +10 pts for 3 wins in a row!"
            if loss_streaks[group].get(participant, 0) == 5:
                streak_msg += f"\nDuck King Alert: {name} hit 5 losses in a row! 🦆 Time to quack back!"

            # Combine highlights
            if streaks or ducks or streak_msg:
                msg += "\nGame Highlights:"
                if streaks:
                    msg += f"\n- Streak Stars: {', '.join(streaks)} hit 3 wins!"
                if ducks:
                    msg += f"\n- Duck Kings: {', '.join(ducks)} with 5 losses! 🦆"
                msg += streak_msg

            msg += f"\nHere’s the tally so far ({group}):\n{get_leaderboard_with_leader(group)}"
            client.messages.create(body=msg,
                                   from_="whatsapp:+919818609093",
                                   to=participant)


# Start schedulers
threading.Thread(target=send_morning_message, daemon=True).start()
threading.Thread(target=fetch_and_update_results, daemon=True).start()
threading.Thread(target=check_cutoffs, daemon=True).start()


# Function to send the pre-approved template message to all participants
def send_welcome_template():
    for participant in participants:
        client.messages.create(
            from_="whatsapp:+919818609093",
            to=participant,
            content_sid=
            "HX81d9b5c0787ca13dc351afa0c6ad8efb",  # Updated Template SID
            content_variables=
            '{"1": "Welcome to Caricket! 🏏 Predict IPL winners daily. Reply ‘join gg’ to join Gossip-Group! How it works: Vote ‘1’ or ‘2’ for a team, ‘PP 1’/‘PP 2’ to double points (once every 5 matches). Win = +pts, Lose/No vote = -10 pts. Get trash talk, streak bonuses, and more!"}'
        )


# Run the welcome template send once at startup (or schedule it)
threading.Thread(target=send_welcome_template, daemon=True).start()


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    sender = request.values.get("From")
    resp = MessagingResponse()

    # Welcome new subscribers with group-specific join code (only gg for now)
    group_codes = {"join gg": "gg"}
    if incoming_msg in group_codes and sender not in subscribed_players[
            group_codes[incoming_msg]]:
        group = group_codes[incoming_msg]
        subscribed_players[group].add(sender)
        name = participants.get(sender, {"name": "Player"})["name"]
        # Add participant to the Conversation
        add_participant_to_conversation(group, sender)
        welcome_msg = (
            f"Hey {name}, you’re now in Caricket (Gossip-Group)! 🏏 Here’s how to play:\n"
            "- **When**: Starts March 22, 7 AM IST pings for each match.\n"
            "- **Vote**: Reply ‘1’ or ‘2’ to pick a team. Multi-match days? Vote one at a time.\n"
            "- **Power Play**: Use ‘PP 1’ or ‘PP 2’ (once every 5 matches) to double your win (+pts) or loss (-pts)!\n"
            "- **Scoring**: Win = +pts (losers’ pool split), Loss/No vote = -10 pts.\n"
            "- **Cutoffs**: Votes lock 1 hr before each match—Power Plays announced then!\n"
            "- **Extras**: Trash talk from winners, +10 pts for 3-win streaks, Duck King 🦆 for 5 losses!\n"
            "Get ready to swing for the fences—pick your first champ!")
        resp.message(welcome_msg)
        return str(resp)

    # Handle voting with optional Power Play
    if incoming_msg in ("1", "2", "pp 1", "pp 2"):
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        today_matches = sorted(
            [(match, details) for match, details in match_schedule.items()
             if datetime.datetime.strptime(
                 details["time"], "%Y-%m-%d %H:%M:%S").replace(
                     tzinfo=datetime.timezone.utc).date() == today],
            key=lambda x: x[1]["time"])
        name = participants.get(sender, {"name": "mate"})["name"]
        group = "gg"  # Only Gossip-Group

        if group not in participants.get(sender, {"groups": []})["groups"]:
            resp.message(
                f"Hey {name}, you need to join Gossip-Group first! Reply with ‘join gg’ to get started."
            )
            return str(resp)

        current_match = next((m for m, d in today_matches
                              if (m, sender) not in predictions[group]), None)
        if not current_match:
            resp.message(
                f"Hey {name}, you’ve voted for all today’s matches! Sit tight for the results! ({group})"
            )
            return str(resp)

        match_time = datetime.datetime.strptime(
            match_schedule[current_match]["time"],
            "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        if now > match_time - datetime.timedelta(hours=1):
            resp.message(
                f"Oops, {name}, you snoozed! {current_match}’s locked—next time, be quick! ({group})"
            )
            return str(resp)

        team1, team2 = match_schedule[current_match]["teams"]
        is_power_play = incoming_msg.startswith("pp")
        vote = incoming_msg[-1]
        team = team1 if vote == "1" else team2
        if is_power_play:
            power_play_count[group][sender] = power_play_count[group].get(
                sender, 0) + 1
            if power_play_count[group][sender] > (
                    len([m
                         for m in match_schedule if m <= current_match]) // 5):
                resp.message(
                    f"Sorry, {name}, you’ve used your Power Play for this stretch in {group}! Vote with ‘1’ or ‘2’ next time."
                )
                return str(resp)
            predictions[group][(current_match, sender)] = f"PP {team}"
        else:
            predictions[group][(current_match, sender)] = team
        leaderboard[group][sender] = leaderboard[group].get(sender, 0)
        pending_votes[group].pop((current_match, sender), None)

        next_match = next(
            (m for m, d in today_matches
             if m != current_match and (m, sender) not in predictions[group]),
            None)
        if next_match:
            next_details = match_schedule[next_match]
            next_team1, next_team2 = next_details["teams"]
            next_venue = next_details["venue"]
            next_cutoff = datetime.datetime.strptime(
                next_details["time"], "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=datetime.timezone.utc) - datetime.timedelta(hours=1)
            next_cutoff_str = (next_cutoff + datetime.timedelta(
                hours=5, minutes=30)).strftime("%I:%M %p IST")
            resp.message(
                f"Nice one, {name}! You’re backing {team} for {current_match}{' with Power Play!' if is_power_play else ''} ({group}). Next up: {next_team1} vs {next_team2} at {next_venue}. Reply ‘1’ or ‘2’. Cutoff: {next_cutoff_str}!"
            )
        else:
            resp.message(
                f"Nice one, {name}! You’re backing {team} for {current_match}{' with Power Play!' if is_power_play else ''} ({group}). All set for today—let’s see if they smash it! 🏏"
            )
        return str(resp)

    # Manual result (admin only)
    if incoming_msg.startswith("result"):
        if sender != "whatsapp:+919810272993":
            resp.message("Only Ram can submit results manually!")
            return str(resp)
        try:
            match, winner = incoming_msg.split(":")[1:]
            match = match.strip()
            winner = winner.strip()
            results[match] = winner
            group = "gg"  # Only Gossip-Group
            update_points(match, winner, group)
            send_personalized_messages(match, winner, group)
            resp.message(f"Manual result: {winner.upper()} won {match}")
        except:
            resp.message("Format: 'Result Match X: TEAM'")
        return str(resp)

    name = participants.get(sender, {"name": "mate"})["name"]
    resp.message(
        f"Hey {name}, reply with ‘join gg’ to join Gossip-Group and get started!"
    )
    return str(resp)


def update_points(match, winner, group):
    losers_pool = 0
    winners = []
    for (m, sender), team in predictions[group].items():
        if m == match:
            if team.lower() == winner.lower():
                winners.append(sender)
            else:
                losers_pool += 10
                leaderboard[group][sender] -= 10
    if winners:
        points_each = losers_pool // len(winners)
        for w in winners:
            leaderboard[group][w] += points_each


def get_leaderboard(group):
    sorted_lb = sorted(leaderboard[group].items(),
                       key=lambda x: x[1],
                       reverse=True)
    return "Leaderboard:\n" + "\n".join(
        f"{participants.get(k, {'name': k.split(':')[1]})['name']}: {v}"
        for k, v in sorted_lb)


def get_leaderboard_with_leader(group):
    sorted_lb = sorted(leaderboard[group].items(),
                       key=lambda x: x[1],
                       reverse=True)
    if not sorted_lb:
        return "No scores yet—get voting!"
    leader_name = participants.get(
        sorted_lb[0][0], {"name": sorted_lb[0][0].split(':')[1]})["name"]
    leader_score = sorted_lb[0][1]
    leaderboard_str = f"**{leader_name}: {leader_score}** 🏆\n"
    for k, v in sorted_lb[1:]:
        name = participants.get(k, {"name": k.split(':')[1]})["name"]
        emoji = "🟢" if v > 0 else "🔴" if v < 0 else ""
        leaderboard_str += f"{name}: {v} {emoji}\n"
    return leaderboard_str


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
