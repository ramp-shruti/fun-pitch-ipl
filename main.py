import requests
from datetime import datetime
import pytz


def convert_epoch_to_ist(epoch_ms):
    gmt_time = datetime.fromtimestamp(epoch_ms / 1000, tz=pytz.UTC)
    ist_time = gmt_time.astimezone(pytz.timezone("Asia/Kolkata"))
    return ist_time.strftime("%Y-%m-%d %H:%M:%S")


url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/upcoming"
headers = {
    "X-RapidAPI-Key":
    "your_rapidapi_key_here",  # Optional if you’re using RapidAPI
    "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
}

response = requests.get(url, headers={})
data = response.json()

print("\n🔍 Sample match titles and types:")
for match_type in data.get("typeMatches", []):
    print(f"📦 matchType = {match_type.get('matchType')}")
    for series in match_type.get("seriesMatches", []):
        series_wrapper = series.get("seriesAdWrapper", {})
        series_name = series_wrapper.get("seriesName", "")
        print(f"  🔹 Series: {series_name}")
        matches = series_wrapper.get("matches", [])
        for m in matches:
            title = m.get("matchInfo", {}).get("matchDesc", "")
            print(f"    🏏 {title}")
