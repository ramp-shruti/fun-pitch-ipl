from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import datetime
import os
import threading
import time
import random
import requests

app = Flask(__name__)

print("Environment variables:", os.environ)

account_sid = os.environ.get('ACCOUNT_SID')
auth_token = os.environ.get('AUTH_TOKEN')
if not account_sid or not auth_token:
    print("Error: ACCOUNT_SID or AUTH_TOKEN not set.")
    exit(1)

client = Client(account_sid, auth_token)

cricapi_key = os.environ.get('CRICAPI_KEY')
if not cricapi_key:
    print("Error: CRICAPI_KEY not set.")
    exit(1)

TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

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

# Match schedule in UTC (converted from IST: subtract 5:30), starting from Match 2
match_schedule = {
    "Match 2": {
        "time": "2025-03-23 10:00:00",  # 15:30 IST
        "teams": ("Sunrisers Hyderabad", "Rajasthan Royals"),
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
        "cricapi_id": "91b007f3-c0af-493f-808a-3f4ae2d66e33"
    },
    "Match 3": {
        "time": "2025-03-23 14:00:00",  # 19:30 IST
        "teams": ("Chennai Super Kings", "Mumbai Indians"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "208d68e5-3fab-4f3b-88e9-29ec4a02d3e2"
    },
    "Match 4": {
        "time": "2025-03-24 14:00:00",  # 19:30 IST
        "teams": ("Delhi Capitals", "Lucknow Super Giants"),
        "venue":
        "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
        "cricapi_id": "c6e97609-d9c1-46eb-805a-e282b34f3bb1"
    },
    "Match 5": {
        "time": "2025-03-25 14:00:00",  # 19:30 IST
        "teams": ("Gujarat Titans", "Punjab Kings"),
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "cricapi_id": "83d70527-5fc4-4fad-8dd2-b88b385f379e"
    },
    "Match 6": {
        "time": "2025-03-26 14:00:00",  # 19:30 IST
        "teams": ("Rajasthan Royals", "Kolkata Knight Riders"),
        "venue": "Barsapara Cricket Stadium, Guwahati",
        "cricapi_id": "fd459f45-6e79-42c5-84e4-d046f291cacf"
    },
    "Match 7": {
        "time": "2025-03-27 14:00:00",  # 19:30 IST
        "teams": ("Sunrisers Hyderabad", "Lucknow Super Giants"),
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
        "cricapi_id": "ab4e0813-1e78-467e-aca0-d80c5cfe7dbd"
    },
    "Match 8": {
        "time": "2025-03-28 14:00:00",  # 19:30 IST
        "teams": ("Chennai Super Kings", "Royal Challengers Bengaluru"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "7431523f-7ccb-4a4a-aed7-5c42fc08464c"
    },
    "Match 9": {
        "time": "2025-03-29 14:00:00",  # 19:30 IST
        "teams": ("Gujarat Titans", "Mumbai Indians"),
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "cricapi_id": "f5ed540f-15c7-4189-a5d4-e54be746a522"
    },
    "Match 10": {
        "time": "2025-03-30 10:00:00",  # 15:30 IST
        "teams": ("Delhi Capitals", "Sunrisers Hyderabad"),
        "venue":
        "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
        "cricapi_id": "af5cf1dd-b3d4-4e8d-8660-e5e27cd5202e"
    },
    "Match 11": {
        "time": "2025-03-30 14:00:00",  # 19:30 IST
        "teams": ("Rajasthan Royals", "Chennai Super Kings"),
        "venue": "Barsapara Cricket Stadium, Guwahati",
        "cricapi_id": "057ce3fb-8117-47fe-bf25-be0ed8a56dd0"
    },
    "Match 12": {
        "time": "2025-03-31 14:00:00",  # 19:30 IST
        "teams": ("Mumbai Indians", "Kolkata Knight Riders"),
        "venue": "Wankhede Stadium, Mumbai",
        "cricapi_id": "075649ef-6ca8-4f50-8143-87814b828ea0"
    },
    "Match 13": {
        "time": "2025-04-01 14:00:00",  # 19:30 IST
        "teams": ("Lucknow Super Giants", "Punjab Kings"),
        "venue":
        "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
        "cricapi_id": "7896feec-8fd6-44ef-aee3-eabb679e6305"
    },
    "Match 14": {
        "time": "2025-04-02 14:00:00",  # 19:30 IST
        "teams": ("Royal Challengers Bengaluru", "Gujarat Titans"),
        "venue": "M.Chinnaswamy Stadium, Bengaluru",
        "cricapi_id": "64e88ffc-606f-4d4f-b848-310f1ec7a98a"
    },
    "Match 15": {
        "time": "2025-04-03 14:00:00",  # 19:30 IST
        "teams": ("Kolkata Knight Riders", "Sunrisers Hyderabad"),
        "venue": "Eden Gardens, Kolkata",
        "cricapi_id": "d5915da0-c08b-4122-bcb0-2c2e1e6e168a"
    },
    "Match 16": {
        "time": "2025-04-04 14:00:00",  # 19:30 IST
        "teams": ("Lucknow Super Giants", "Mumbai Indians"),
        "venue":
        "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
        "cricapi_id": "5dc7a22f-5057-4895-bb98-965d9a1f004e"
    },
    "Match 17": {
        "time": "2025-04-05 10:00:00",  # 15:30 IST
        "teams": ("Chennai Super Kings", "Delhi Capitals"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "f5dabb5b-a934-4666-a368-7134e991f569"
    },
    "Match 18": {
        "time": "2025-04-05 14:00:00",  # 19:30 IST
        "teams": ("Punjab Kings", "Rajasthan Royals"),
        "venue":
        "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, Chandigarh",
        "cricapi_id": "b2e603ab-96f7-4711-ac9f-6a78e742237d"
    },
    "Match 19": {
        "time": "2025-04-06 10:00:00",  # 15:30 IST
        "teams": ("Kolkata Knight Riders", "Lucknow Super Giants"),
        "venue": "Eden Gardens, Kolkata",
        "cricapi_id": "2ac97990-6265-40e4-b93e-fcd24e89026c"
    },
    "Match 20": {
        "time": "2025-04-06 14:00:00",  # 19:30 IST
        "teams": ("Sunrisers Hyderabad", "Gujarat Titans"),
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
        "cricapi_id": "3027ad1a-e7d8-4891-8ea0-1a56f81e8700"
    },
    "Match 21": {
        "time": "2025-04-07 14:00:00",  # 19:30 IST
        "teams": ("Mumbai Indians", "Royal Challengers Bengaluru"),
        "venue": "Wankhede Stadium, Mumbai",
        "cricapi_id": "0a5ebe67-67a3-41d2-bbc8-5fc94aef0529"
    },
    "Match 22": {
        "time": "2025-04-08 14:00:00",  # 19:30 IST
        "teams": ("Punjab Kings", "Chennai Super Kings"),
        "venue":
        "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, Chandigarh",
        "cricapi_id": "56a88e0e-e844-41bd-ba65-3c905e36ba0d"
    },
    "Match 23": {
        "time": "2025-04-09 14:00:00",  # 19:30 IST
        "teams": ("Gujarat Titans", "Rajasthan Royals"),
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "cricapi_id": "71213f27-c274-48b0-97f7-ec74e895dcbe"
    },
    "Match 24": {
        "time": "2025-04-10 14:00:00",  # 19:30 IST
        "teams": ("Royal Challengers Bengaluru", "Delhi Capitals"),
        "venue": "M.Chinnaswamy Stadium, Bengaluru",
        "cricapi_id": "3f309c2d-75dd-48bc-9d9f-e3979e252949"
    },
    "Match 25": {
        "time": "2025-04-11 14:00:00",  # 19:30 IST
        "teams": ("Chennai Super Kings", "Kolkata Knight Riders"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "b39bbd39-c67f-4892-9a48-02e958946718"
    },
}

# Data storage for both groups
predictions = {"gg": {}, "caricket": {}}
leaderboard = {"gg": {}, "caricket": {}}
results = {}  # Shared across groups
subscribed_players = {"gg": set(), "caricket": set()}
pending_votes = {"gg": {}, "caricket": {}}
power_play_count = {"gg": {}, "caricket": {}}
power_play_max = 3  # Base max, increases to 5 for 5+ wins
win_streaks = {"gg": {}, "caricket": {}}
loss_streaks = {"gg": {}, "caricket": {}}

# Participants for both groups
participants = {
    # Gossip Group (gg)
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
    # Caricket group (excluding gg overlaps)
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

subscriptions = {
    p: {
        "subscribed": False,
        "last_interaction": None,
        "conversation_started": False
    }
    for p in participants
}
message_logs = {p: {"sent": [], "received": []} for p in participants}
admin = "whatsapp:+919810272993"
conversation_sids = {"gg": None, "caricket": None}

trash_talk = [
    "{winner} says: 'Better luck next time, {loser}!' 😜",
    "{winner} to {loser}: 'Did you even watch the game?' 📺",
    "{winner} laughs: '{loser}, your team’s still warming up!' 😂",
    "{winner} taunts: '{loser}, stick to cheering, not picking!' 📣",
    "{winner} smirks: 'Looks like {loser} picked the wrong team!' 😏",
    "{winner} to {loser}: 'Maybe next time, champ!' 🏅",
    "{winner} chuckles: '{loser}, your team needs a miracle!' 🙏",
    "{winner} teases: 'Nice try, {loser}, but not today!' 😉",
    "{winner} to {loser}: 'Better luck in the next match!' 🍀",
    "{winner} boasts: '{loser}, my team’s on fire!' 🔥",
    "{winner} to {loser}: 'Did you really think you’d win?' 🤔",
    "{winner} laughs: '{loser}, your team’s out of steam!' 💨",
    "{winner} to {loser}: 'Keep dreaming, pal!' 💭",
    "{winner} taunts: '{loser}, my team’s unstoppable!' 💪",
    "{winner} to {loser}: 'Sorry, but my team’s the best!' 🏆",
    "{winner} teases: '{loser}, better luck next season!' 📅",
    "{winner} to {loser}: 'Looks like you need a new strategy!' 🧠",
    "{winner} mocks: '{loser}, your team’s all talk, no action!' 🗣️",
    "{winner} to {loser}: 'Tough break, better luck next time!' 😅",
    "{winner} cheers: 'My team’s the real deal, {loser}!' 🎉"
]

vote_acknowledgments = [
    "Cool {name} - you are backing {team}! 😎",
    "Go {team} Go! Nice pick, {name}! 🏏",
    "Hopefully {team} wins, {name} - great choice! 🍀",
    "Awesome, {name}! You’re rooting for {team}! 🏆",
    "Let’s see if {team} pulls through for you, {name}! 👀",
    "Nice one, {name}! {team} has your vote! 👍",
    "You’re all in for {team}, {name} - good luck! 🍀",
    "Sweet choice, {name}! {team} better not let you down! 💪",
    "Got it, {name}! You’re cheering for {team}! 📣",
    "Alright, {name}! {team} is your team to win! 🏅",
    "You've backed {team} — may the odds be ever in your favor! 🍀",
    "Locked in! Let's go, {team}! 🔥", "Awesome, you're with {team} today! 🏆",
    "{team} it is! Hope they smash it today! 💥",
    "Nice pick — {team} could take it home! 🎯",
    "Cool, {team} it is. Let’s see how this plays out! 👀",
    "Great! You’re backing {team}. Bold move! 💪",
    "Cheers! {team} has your vote! 🍻",
    "Hopefully {team} brings the fireworks today! 🎆",
    "Sweet! {name}, you’re all set with {team}! 🚀"
]


def send_whatsapp_message(participant, message_body):
    try:
        print(f"Sending to {participant}: {message_body}")
        message = client.messages.create(body=message_body,
                                         from_=TWILIO_WHATSAPP_NUMBER,
                                         to=participant)
        message_logs[participant]["sent"].append({
            "timestamp":
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "message":
            message_body,
            "sid":
            message.sid
        })
    except TwilioRestException as e:
        print(f"Twilio error for {participant}: {e}")
    except Exception as e:
        print(f"Error sending to {participant}: {e}")


def is_player_active(participant):
    sub = subscriptions[participant]
    if not sub["subscribed"] or not sub["conversation_started"] or not sub[
            "last_interaction"]:
        return False
    time_since = (datetime.datetime.now(datetime.timezone.utc) -
                  sub["last_interaction"]).total_seconds()
    return time_since <= 24 * 60 * 60


def send_action_menu(participant):
    message_body = ("🏏 **Caricket Action Time!**\n\n"
                    "🔹 V️ **Vote for Matches** 🏆\n"
                    "🔹 W️ **Who’s Where?** 📊\n"
                    "🔹 P️ **Points Table** 🚀\n"
                    "🔹 M️ **My Votes** 🗳️\n\n"
                    "💬 Reply *V*, *W*, *P*, or *M* to choose!")
    send_whatsapp_message(participant, message_body)


def send_vote_prompt(participant, match, details, group):
    match_number = match.split(" ")[1] if "Match" in match else match
    team1_full, team2_full = details["teams"]
    team1, team2 = team_acronyms[team1_full], team_acronyms[team2_full]
    venue = details["venue"].split(",")[-1].strip()
    match_time = datetime.datetime.strptime(
        details["time"],
        "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    # Convert UTC to IST by adding 5 hours and 30 minutes
    match_time_ist = match_time + datetime.timedelta(hours=5, minutes=30)
    cutoff_time_str = match_time_ist.strftime(
        "%I:%M %p IST on %B %d, %Y")  # Cutoff at match start in IST
    pp_used = power_play_count[group].get(participant, 0)
    pp_max = 5 if win_streaks[group].get(participant,
                                         0) >= 5 else power_play_max
    remaining_pp = pp_max - pp_used
    message_body = (
        f"🏏 **{match}: {team1} 🆚 {team2}** ({group})\n"
        f"📍 *Venue:* {venue}\n\n"
        f"🔥 **Who are you backing?**\n"
        f"Reply *'1'* for **{team1}**\n"
        f"Reply *'2'* for **{team2}**\n\n"
        f"💥 Power Play it with 'PP 1' or 'PP 2' ({remaining_pp} PP votes remaining)!\n"
        f"⏳ **Vote before:** {cutoff_time_str}!")
    send_whatsapp_message(participant, message_body)


def show_current_votes(participant):
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    upcoming = sorted(
        [(m, d) for m, d in match_schedule.items()
         if datetime.datetime.strptime(d["time"], "%Y-%m-%d %H:%M:%S").replace(
             tzinfo=datetime.timezone.utc).date() >= today],
        key=lambda x: x[1]["time"])
    sender_groups = participants[participant]["groups"]
    message = ""
    for group in sender_groups:
        current_match = next(
            (m for m, d in upcoming if now <= datetime.datetime.strptime(
                d["time"], "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=datetime.timezone.utc)), None)
        if not current_match:
            name = participants[participant]["name"]
            message += f"No upcoming matches to show votes for in {group}, {name}! Wait for the next one...\n\n"
            continue
        team1, team2 = match_schedule[current_match]["teams"]
        team1_short, team2_short = team_acronyms[team1], team_acronyms[team2]
        message += f"🏏 **{current_match}: {team1_short} 🆚 {team2_short}** ({group})\n\n🗳️ **Who’s Where?**\n"
        for p in participants:
            if group not in participants[p]["groups"]:
                continue
            name = participants[p]["name"]
            if (current_match, p) in predictions[group]:
                team = predictions[group][(current_match,
                                           p)].replace("PP ", "")
                is_power_play = predictions[group][(current_match,
                                                    p)].startswith("PP")
                message += f"- {name}: {team}{' (PP)' if is_power_play else ''}\n"
            else:
                message += f"- {name}: No vote yet\n"
        message += "\n"
    send_whatsapp_message(participant, message.strip())
    send_action_menu(participant)


def show_my_votes(participant):
    sender_groups = participants[participant]["groups"]
    name = participants[participant]["name"]
    message = ""
    # Since votes are now shared for multi-group players, show votes once
    group = sender_groups[0]  # Use the first group to fetch votes
    message += f"🏏 **Your Votes, {name}** (Shared across groups):\n"
    voted = False
    for match, details in match_schedule.items():
        if (match, participant) in predictions[group]:
            team = predictions[group][(match, participant)].replace("PP ", "")
            is_power_play = predictions[group][(match,
                                                participant)].startswith("PP")
            match_time = datetime.datetime.strptime(
                details["time"],
                "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            # Convert UTC to IST for display
            match_time_ist = match_time + datetime.timedelta(hours=5,
                                                             minutes=30)
            time_str = match_time_ist.strftime("%B %d, %I:%M %p IST")
            team1, team2 = details["teams"]
            message += f"- {match} ({time_str}): {team}{' (PP)' if is_power_play else ''}\n"
            voted = True
    if not voted:
        message += "You haven’t cast any votes yet! 🗳️\n"
    message += "\n"
    send_whatsapp_message(participant, message.strip())
    send_action_menu(participant)


def handle_unrecognized_message(sender, message):
    name = participants[sender]["name"]
    return (
        f"Sorry {name}, I didn’t catch that! 😅 Let’s get back to Caricket—reply *V* to vote, *W* to see who’s where, "
        f"*P* for points, or *M* to check your votes! 🏏")


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
            finish_time = match_time + datetime.timedelta(hours=3, minutes=30)
            if match_date == today and now > finish_time:
                match_id = details["cricapi_id"]
                match_info_url = f"https://api.cricapi.com/v1/match_info?apikey={cricapi_key}&id={match_id}"
                try:
                    response = requests.get(match_info_url)
                    response.raise_for_status()
                    match_data = response.json()
                except requests.exceptions.RequestException as e:
                    print(
                        f"Error fetching match info for {match} (ID: {match_id}): {e}"
                    )
                    continue
                if "data" not in match_data or "matchWinner" not in match_data[
                        "data"]:
                    print(f"No winner for {match} (ID: {match_id}).")
                    continue
                winner = match_data["data"]["matchWinner"]
                if not winner:
                    print(f"Null winner for {match} (ID: {match_id}).")
                    continue
                team1, team2 = details["teams"]
                if winner not in [team1, team2]:
                    print(f"Invalid winner for {match}: {winner}.")
                    continue
                results[match] = winner
                loser = team1 if winner == team2 else team2
                for group in ["gg", "caricket"]:
                    for participant in participants:
                        if group not in participants[participant]["groups"]:
                            continue
                        if (match, participant) not in predictions[group]:
                            predictions[group][(match, participant)] = loser
                            match_number = int(match.split(" ")[1])
                            pp_used = power_play_count[group].get(
                                participant, 0)
                            pp_max = 5 if win_streaks[group].get(
                                participant, 0) >= 5 else power_play_max
                            if match_number > 12 and pp_used < pp_max:
                                remaining_pp = pp_max - pp_used
                                if 15 - match_number + 1 <= remaining_pp:
                                    predictions[group][(
                                        match, participant)] = f"PP {loser}"
                                    power_play_count[group][
                                        participant] = pp_used + 1
                    update_points(match, winner, group)
                    send_personalized_messages(match, winner, group)
        time.sleep(300)


def send_personalized_messages(match, winner, group):
    losers_pool = 0
    winners = []
    for (m, sender), team in predictions[group].items():
        if m == match:
            team_name = team.replace("PP ", "")
            is_power_play = team.startswith("PP")
            if team_name.lower() == winner.lower():
                winners.append(sender)
            else:
                losers_pool += 10
                leaderboard[group][sender] = leaderboard[group].get(
                    sender, 0) - (20 if is_power_play else 10)
    points_each = losers_pool // len(winners) if winners else 0

    streaks = [
        p for p in participants if group in participants[p]["groups"]
        and win_streaks[group].get(p, 0) == 3
    ]
    extra_pp = [
        p for p in participants if group in participants[p]["groups"]
        and win_streaks[group].get(p, 0) >= 5
    ]
    ducks = [
        p for p in participants if group in participants[p]["groups"]
        and loss_streaks[group].get(p, 0) == 5
    ]

    message = f"Results for {match}: {winner.upper()} won! ({group})\n\nVotes:\n"
    for (m, sender), team in predictions[group].items():
        if m == match:
            name = participants[sender]["name"]
            message += f"- {name}: {team}\n"
    message += "\nScores:\n"
    for participant in participants:
        if group not in participants[participant]["groups"]:
            continue
        name = participants[participant]["name"]
        if (match, participant) in predictions[group]:
            team = predictions[group][(match, participant)].replace("PP ", "")
            is_power_play = predictions[group][(match,
                                                participant)].startswith("PP")
            if team.lower() == winner.lower():
                win_streaks[group][participant] = win_streaks[group].get(
                    participant, 0) + 1
                loss_streaks[group][participant] = 0
                points = points_each * 2 if is_power_play else points_each
                if win_streaks[group][participant] == 3:
                    points += 10  # +10 for 3 wins
                leaderboard[group][participant] = leaderboard[group].get(
                    participant, 0) + points
                message += f"- {name}: +{points} pts{' (PP)' if is_power_play else ''}\n"
            else:
                loss_streaks[group][participant] = loss_streaks[group].get(
                    participant, 0) + 1
                win_streaks[group][participant] = 0
                points = -20 if is_power_play else -10
                leaderboard[group][participant] = leaderboard[group].get(
                    participant, 0) + points
                message += f"- {name}: {points} pts{' (PP)' if is_power_play else ''}\n"
        else:
            message += f"- {name}: -10 pts (no vote)\n"

    if winners:
        winner_name = participants.get(random.choice(winners),
                                       {"name": "a champ"})["name"]
        for participant in participants:
            if group not in participants[participant]["groups"]:
                continue
            if participant not in winners and predictions[group].get(
                (match, participant)):
                loser_name = participants[participant]["name"]
                trash = random.choice(trash_talk).format(winner=winner_name,
                                                         loser=loser_name)
                message += f"\n{trash}"

    streak_msg = ""
    if streaks:
        streak_names = ", ".join(participants[p]["name"] for p in streaks)
        streak_msg += f"\nStreak Bonuses: {streak_names} scored +10 pts each for 3 wins in a row!"
    if extra_pp:
        extra_pp_names = ", ".join(participants[p]["name"] for p in extra_pp)
        streak_msg += f"\nExtra PP Rights: {extra_pp_names} earned 2 extra PP votes for 5+ wins!"
        for p in extra_pp:
            if power_play_count[group].get(p, 0) <= power_play_max:
                power_play_count[group][p] = power_play_count[group].get(p, 0)
    if ducks:
        duck_names = ", ".join(participants[p]["name"] for p in ducks)
        streak_msg += f"\nDuck Kings: {duck_names} hit 5 losses! 🦆"

    if streaks or extra_pp or ducks:
        message += f"\nGame Highlights:{streak_msg}"

    message += f"\nHere’s the tally so far ({group}):\n{get_leaderboard_with_leader(group)}"
    send_whatsapp_message(admin, message)


threading.Thread(target=fetch_and_update_results, daemon=True).start()


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    sender = request.values.get("From")
    resp = MessagingResponse()

    print(f"Received from {sender}: {incoming_msg}")
    message_logs[sender]["received"].append({
        "timestamp":
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "message":
        incoming_msg
    })

    subscriptions[sender]["last_interaction"] = datetime.datetime.now(
        datetime.timezone.utc)
    if not subscriptions[sender]["subscribed"]:
        subscriptions[sender]["subscribed"] = True
        for group in participants[sender]["groups"]:
            power_play_count[group][sender] = 0

    if incoming_msg == "hi":
        subscriptions[sender]["conversation_started"] = True
        send_action_menu(sender)
        return str(resp)

    # Determine the group(s) the sender belongs to
    sender_groups = participants[sender]["groups"]

    if incoming_msg == "v":
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        upcoming = sorted(
            [(m, d)
             for m, d in match_schedule.items() if datetime.datetime.strptime(
                 d["time"], "%Y-%m-%d %H:%M:%S").replace(
                     tzinfo=datetime.timezone.utc).date() >= today],
            key=lambda x: x[1]["time"])
        # Check if the player has already voted in any group
        for match, details in upcoming:
            has_voted = False
            for group in sender_groups:
                if (match, sender) in predictions[group]:
                    has_voted = True
                    break
            if has_voted:
                continue  # Skip if already voted in any group
            # Prompt for the first unvoted match
            group = sender_groups[0]  # Use the first group for the prompt
            send_vote_prompt(sender, match, details, group)
            pending_votes[group][(match, sender)] = None
            break
        else:
            name = participants[sender]["name"]
            send_whatsapp_message(
                sender,
                f"Hey {name}, you’ve voted for all upcoming matches! Sit tight!"
            )
            send_action_menu(sender)
        return str(resp)

    if incoming_msg == "w":
        show_current_votes(sender)
        return str(resp)

    if incoming_msg == "p":
        message = ""
        for group in sender_groups:
            message += f"Points Table ({group}):\n{get_leaderboard_with_leader(group)}\n\n"
        send_whatsapp_message(sender, message.strip())
        send_action_menu(sender)
        return str(resp)

    if incoming_msg == "m":
        show_my_votes(sender)
        return str(resp)

    if incoming_msg in ("1", "2", "pp 1", "pp 2"):
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        upcoming = sorted(
            [(m, d)
             for m, d in match_schedule.items() if datetime.datetime.strptime(
                 d["time"], "%Y-%m-%d %H:%M:%S").replace(
                     tzinfo=datetime.timezone.utc).date() >= today],
            key=lambda x: x[1]["time"])
        name = participants[sender]["name"]
        # Find the first match the player hasn’t voted for in any group
        current_match = None
        for match, details in upcoming:
            has_voted = False
            for group in sender_groups:
                if (match, sender) in predictions[group]:
                    has_voted = True
                    break
            if not has_voted:
                current_match = match
                break
        if not current_match:
            send_whatsapp_message(
                sender,
                f"Hey {name}, you’ve voted for all matches! Sit tight!")
            send_action_menu(sender)
            return str(resp)
        match_time = datetime.datetime.strptime(
            match_schedule[current_match]["time"],
            "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        if now > match_time:  # Cutoff at match start
            send_whatsapp_message(
                sender, f"Oops, {name}, {current_match} has started—too late!")
            send_action_menu(sender)
            return str(resp)
        team1, team2 = match_schedule[current_match]["teams"]
        is_power_play = incoming_msg.startswith("pp")
        vote = incoming_msg[-1]
        team = team1 if vote == "1" else team2
        # Record the vote in all groups the player belongs to
        for group in sender_groups:
            pp_max = 5 if win_streaks[group].get(sender,
                                                 0) >= 5 else power_play_max
            if is_power_play:
                pp_used = power_play_count[group].get(sender, 0)
                if pp_used < pp_max:
                    power_play_count[group][sender] = pp_used + 1
                    predictions[group][(current_match, sender)] = f"PP {team}"
                else:
                    predictions[group][(current_match, sender)] = team
                    send_whatsapp_message(
                        sender,
                        f"No PP left, {name}! Normal vote for {team} recorded. ({group})"
                    )
            else:
                predictions[group][(current_match, sender)] = team
            leaderboard[group][sender] = leaderboard[group].get(sender, 0)
            pending_votes[group].pop((current_match, sender), None)
        acknowledgment = random.choice(vote_acknowledgments).format(name=name,
                                                                    team=team)
        send_whatsapp_message(sender, acknowledgment)
        # Find the next match to vote on
        next_match = None
        for match, details in upcoming:
            has_voted = False
            for group in sender_groups:
                if (match, sender) in predictions[group]:
                    has_voted = True
                    break
            if not has_voted:
                next_match = match
                break
        if next_match:
            group = sender_groups[0]  # Use the first group for the prompt
            send_vote_prompt(sender, next_match, match_schedule[next_match],
                             group)
            pending_votes[group][(next_match, sender)] = None
        else:
            send_whatsapp_message(sender,
                                  f"Nice one, {name}! All matches voted!")
            send_action_menu(sender)
        return str(resp)

    if incoming_msg.startswith("result"):
        if sender != admin:
            send_whatsapp_message(sender,
                                  "Only Ram can submit results manually!")
            return str(resp)
        try:
            match, winner = incoming_msg.split(":")[1:]
            match, winner = match.strip(), winner.strip()
            results[match] = winner
            for group in ["gg", "caricket"]:
                update_points(match, winner, group)
                send_personalized_messages(match, winner, group)
            send_whatsapp_message(
                sender, f"Manual result: {winner.upper()} won {match}")
        except:
            send_whatsapp_message(sender, "Format: 'Result Match X: TEAM'")
        return str(resp)

    response = handle_unrecognized_message(sender, incoming_msg)
    send_whatsapp_message(sender, response)
    return str(resp)


def update_points(match, winner, group):
    losers_pool = 0
    winners = []
    for (m, sender), team in predictions[group].items():
        if m == match:
            team_name = team.replace("PP ", "")
            is_power_play = team.startswith("PP")
            if team_name.lower() == winner.lower():
                winners.append(sender)
            else:
                losers_pool += 10
                leaderboard[group][sender] = leaderboard[group].get(
                    sender, 0) - (20 if is_power_play else 10)
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
        sorted_lb[0][0], {"name": sorted_lb[0][0].split(':')[1]})['name']
    leader_score = sorted_lb[0][1]
    leaderboard_str = f"**{leader_name}: {leader_score}** 🏆\n"
    for k, v in sorted_lb[1:]:
        name = participants.get(k, {"name": k.split(':')[1]})['name']
        emoji = "🟢" if v > 0 else "🔴" if v < 0 else ""
        leaderboard_str += f"{name}: {v} {emoji}\n"
    return leaderboard_str


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
