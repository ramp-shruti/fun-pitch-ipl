# setup.py
from database import init_db, insert_group, insert_match, get_db_connection, fetch_existing_id
import datetime
from zoneinfo import ZoneInfo

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

match_schedule = {
    "Match 2": {
        "time": "2025-03-23 10:00:00",
        "teams": ("Sunrisers Hyderabad", "Rajasthan Royals"),
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
        "cricapi_id": "91b007f3-c0af-493f-808a-3f4ae2d66e33"
    },
    "Match 3": {
        "time": "2025-03-23 14:00:00",
        "teams": ("Chennai Super Kings", "Mumbai Indians"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "208d68e5-3fab-4f3b-88e9-29ec4a02d3e2"
    },
    "Match 4": {
        "time": "2025-03-24 14:00:00",
        "teams": ("Delhi Capitals", "Lucknow Super Giants"),
        "venue":
        "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
        "cricapi_id": "c6e97609-d9c1-46eb-805a-e282b34f3bb1"
    },
    "Match 5": {
        "time": "2025-03-25 14:00:00",
        "teams": ("Gujarat Titans", "Punjab Kings"),
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "cricapi_id": "83d70527-5fc4-4fad-8dd2-b88b385f379e"
    },
    "Match 6": {
        "time": "2025-03-26 14:00:00",
        "teams": ("Rajasthan Royals", "Kolkata Knight Riders"),
        "venue": "Barsapara Cricket Stadium, Guwahati",
        "cricapi_id": "fd459f45-6e79-42c5-84e4-d046f291cacf"
    },
    "Match 7": {
        "time": "2025-03-27 14:00:00",
        "teams": ("Sunrisers Hyderabad", "Lucknow Super Giants"),
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
        "cricapi_id": "ab4e0813-1e78-467e-aca0-d80c5cfe7dbd"
    },
    "Match 8": {
        "time": "2025-03-28 14:00:00",
        "teams": ("Chennai Super Kings", "Royal Challengers Bengaluru"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "7431523f-7ccb-4a4a-aed7-5c42fc08464c"
    },
    "Match 9": {
        "time": "2025-03-29 14:00:00",
        "teams": ("Gujarat Titans", "Mumbai Indians"),
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "cricapi_id": "f5ed540f-15c7-4189-a5d4-e54be746a522"
    },
    "Match 10": {
        "time": "2025-03-30 10:00:00",
        "teams": ("Delhi Capitals", "Sunrisers Hyderabad"),
        "venue":
        "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
        "cricapi_id": "af5cf1dd-b3d4-4e8d-8660-e5e27cd5202e"
    },
    "Match 11": {
        "time": "2025-03-30 14:00:00",
        "teams": ("Rajasthan Royals", "Chennai Super Kings"),
        "venue": "Barsapara Cricket Stadium, Guwahati",
        "cricapi_id": "057ce3fb-8117-47fe-bf25-be0ed8a56dd0"
    },
    "Match 12": {
        "time": "2025-03-31 14:00:00",
        "teams": ("Mumbai Indians", "Kolkata Knight Riders"),
        "venue": "Wankhede Stadium, Mumbai",
        "cricapi_id": "075649ef-6ca8-4f50-8143-87814b828ea0"
    },
    "Match 13": {
        "time": "2025-04-01 14:00:00",
        "teams": ("Lucknow Super Giants", "Punjab Kings"),
        "venue":
        "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
        "cricapi_id": "7896feec-8fd6-44ef-aee3-eabb679e6305"
    },
    "Match 14": {
        "time": "2025-04-02 14:00:00",
        "teams": ("Royal Challengers Bengaluru", "Gujarat Titans"),
        "venue": "M.Chinnaswamy Stadium, Bengaluru",
        "cricapi_id": "64e88ffc-606f-4d4f-b848-310f1ec7a98a"
    },
    "Match 15": {
        "time": "2025-04-03 14:00:00",
        "teams": ("Kolkata Knight Riders", "Sunrisers Hyderabad"),
        "venue": "Eden Gardens, Kolkata",
        "cricapi_id": "d5915da0-c08b-4122-bcb0-2c2e1e6e168a"
    },
    "Match 16": {
        "time": "2025-04-04 14:00:00",
        "teams": ("Lucknow Super Giants", "Mumbai Indians"),
        "venue":
        "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
        "cricapi_id": "5dc7a22f-5057-4895-bb98-965d9a1f004e"
    },
    "Match 17": {
        "time": "2025-04-05 10:00:00",
        "teams": ("Chennai Super Kings", "Delhi Capitals"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "f5dabb5b-a934-4666-a368-7134e991f569"
    },
    "Match 18": {
        "time": "2025-04-05 14:00:00",
        "teams": ("Punjab Kings", "Rajasthan Royals"),
        "venue":
        "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, Chandigarh",
        "cricapi_id": "b2e603ab-96f7-4711-ac9f-6a78e742237d"
    },
    "Match 19": {
        "time": "2025-04-06 10:00:00",
        "teams": ("Kolkata Knight Riders", "Lucknow Super Giants"),
        "venue": "Eden Gardens, Kolkata",
        "cricapi_id": "2ac97990-6265-40e4-b93e-fcd24e89026c"
    },
    "Match 20": {
        "time": "2025-04-06 14:00:00",
        "teams": ("Sunrisers Hyderabad", "Gujarat Titans"),
        "venue": "Rajiv Gandhi International Stadium, Hyderabad",
        "cricapi_id": "3027ad1a-e7d8-4891-8ea0-1a56f81e8700"
    },
    "Match 21": {
        "time": "2025-04-07 14:00:00",
        "teams": ("Mumbai Indians", "Royal Challengers Bengaluru"),
        "venue": "Wankhede Stadium, Mumbai",
        "cricapi_id": "0a5ebe67-67a3-41d2-bbc8-5fc94aef0529"
    },
    "Match 22": {
        "time": "2025-04-08 14:00:00",
        "teams": ("Punjab Kings", "Chennai Super Kings"),
        "venue":
        "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, Chandigarh",
        "cricapi_id": "56a88e0e-e844-41bd-ba65-3c905e36ba0d"
    },
    "Match 23": {
        "time": "2025-04-09 14:00:00",
        "teams": ("Gujarat Titans", "Rajasthan Royals"),
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "cricapi_id": "71213f27-c274-48b0-97f7-ec74e895dcbe"
    },
    "Match 24": {
        "time": "2025-04-10 14:00:00",
        "teams": ("Royal Challengers Bengaluru", "Delhi Capitals"),
        "venue": "M.Chinnaswamy Stadium, Bengaluru",
        "cricapi_id": "3f309c2d-75dd-48bc-9d9f-e3979e252949"
    },
    "Match 25": {
        "time": "2025-04-11 14:00:00",
        "teams": ("Chennai Super Kings", "Kolkata Knight Riders"),
        "venue": "MA Chidambaram Stadium, Chennai",
        "cricapi_id": "b39bbd39-c67f-4892-9a48-02e958946718"
    },
}

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


def setup_data(clear_votes=False, update_existing=False):
    init_db()
    group_ids = {}
    for name in ["gg", "caricket"]:
        existing_id = fetch_existing_id("groups", "name", name)
        if existing_id:
            group_ids[name] = existing_id
        else:
            group_ids[name] = insert_group(name)

    for match_name, details in match_schedule.items():
        match_time = datetime.datetime.strptime(
            details["time"],
            "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
        existing_id = fetch_existing_id("matches", "match_name", match_name)
        if existing_id and update_existing:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE matches SET team1 = %s, team2 = %s, venue = %s, match_time = %s, cricapi_id = %s
                        WHERE match_name = %s
                    """, (details["teams"][0], details["teams"][1],
                          details["venue"], match_time, details["cricapi_id"],
                          match_name))
                    conn.commit()
        elif not existing_id:
            insert_match(match_name, details["teams"][0], details["teams"][1],
                         details["venue"], match_time, details["cricapi_id"])

    if clear_votes:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE votes, results, scores RESTART IDENTITY")
                conn.commit()
                print("Votes, results, and scores cleared.")
    print("Setup complete!")


def reset_database():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS scores CASCADE;
                DROP TABLE IF EXISTS results CASCADE;
                DROP TABLE IF EXISTS votes CASCADE;
                DROP TABLE IF EXISTS matches CASCADE;
                DROP TABLE IF EXISTS active_participants CASCADE;
                DROP TABLE IF EXISTS group_participants CASCADE;
                DROP TABLE IF EXISTS participants CASCADE;
                DROP TABLE IF EXISTS groups CASCADE;
            """)
            conn.commit()
            print("Database reset complete!")


if __name__ == "__main__":
    reset_database()
    setup_data()
