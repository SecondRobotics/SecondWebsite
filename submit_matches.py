import csv
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('SRC_API_TOKEN')
API_BASE_URL = 'https://secondrobotics.org'

def submit_match(red_alliance, blue_alliance, red_score, blue_score):
    url = f"{API_BASE_URL}/ranked/api/CR3v3/match"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    payload = {
        "red_alliance": red_alliance,
        "blue_alliance": blue_alliance,
        "red_score": red_score,
        "blue_score": blue_score
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def process_csv(file_path):
    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row if present
        
        for row in reader:
            red_alliance = [int(player.strip()) for player in row[:3]]
            blue_alliance = [int(player.strip()) for player in row[3:6]]
            red_score = int(row[6])
            blue_score = int(row[7])
            
            result = submit_match(red_alliance, blue_alliance, red_score, blue_score)
            print(f"Match submitted: {result}")

def get_valid_players(game_mode_code):
    url = f"{API_BASE_URL}/ranked/api/{game_mode_code}/players/"
    headers = {
        'X-API-KEY': API_KEY
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch valid players: {response.status_code}")
        return None

if __name__ == "__main__":
    csv_file_path = "matches.csv"  # Replace with your CSV file path
    game_mode_code = "CR3v3"  # Replace with the appropriate game mode code
    
    valid_players = get_valid_players(game_mode_code)
    if valid_players:
        print(f"Fetched {len(valid_players)} valid players")
        # You can use valid_players for validation or other purposes
    
    process_csv(csv_file_path)