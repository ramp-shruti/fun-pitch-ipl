# messaging.py
import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import timedelta
from zoneinfo import ZoneInfo

account_sid = os.environ.get('ACCOUNT_SID')
auth_token = os.environ.get('AUTH_TOKEN')
client = Client(account_sid, auth_token)
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Replace with your Twilio WhatsApp number

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


def send_message(to, body):
    try:
        message = client.messages.create(body=body,
                                         from_=TWILIO_WHATSAPP_NUMBER,
                                         to=to)
        print(f"Sent to {to}: {body} (SID: {message.sid})")
    except TwilioRestException as e:
        print(f"Twilio error for {to}: {e}")
    except Exception as e:
        print(f"Error sending to {to}: {e}")


def send_vote_prompt(phone, match, db):
    with db.cursor() as cur:
        cur.execute("SELECT name FROM participants WHERE phone = %s",
                    (phone, ))
        name = cur.fetchone()["name"]
        cur.execute(
            "SELECT team1, team2, venue, match_time FROM matches WHERE match_name = %s",
            (match, ))
        match_data = cur.fetchone()
        match_time_ist = match_data["match_time"] + timedelta(hours=5,
                                                              minutes=30)
        message = (
            f"🏏 **{match}: {team_acronyms[match_data['team1']]} 🆚 {team_acronyms[match_data['team2']]}**\n"
            f"📍 *Venue:* {match_data['venue'].split(',')[-1].strip()}\n\n"
            f"🔥 **Who are you backing, {name}?**\n"
            f"Reply *'1'* for **{team_acronyms[match_data['team1']]}**\n"
            f"Reply *'2'* for **{team_acronyms[match_data['team2']]}**\n\n"
            f"💥 Power Play it with 'PP 1' or 'PP 2'!\n"
            f"⏳ **Vote before:** {match_time_ist.strftime('%I:%M %p IST on %B %d, %Y')}!"
        )
        send_message(phone, message)
