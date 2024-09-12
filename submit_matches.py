import csv
import requests
import os
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError

# Load environment variables
load_dotenv()

API_KEY = os.getenv('SRC_API_TOKEN')
API_BASE_URL = 'https://secondrobotics.org'

def get_all_users():
    url = f"{API_BASE_URL}/api/ranked/all-users/"
    response = requests.get(url)
    if response.status_code == 200:
        users = response.json()
        # Filter out users with incorrect ID length
        return [user for user in users if len(str(user['id'])) == 18]
    else:
        print(f"Failed to fetch users: {response.status_code}")
        return None

def find_closest_match(name, all_users):
    best_match = None
    best_ratio = 0
    for user in all_users:
        ratio_display = fuzz.ratio(name.lower(), user['display_name'].lower())
        ratio_username = fuzz.ratio(name.lower(), user['username'].lower())
        max_ratio = max(ratio_display, ratio_username)
        if max_ratio > best_ratio:
            best_ratio = max_ratio
            best_match = user
    return best_match, best_ratio

def validate_player_id(text):
    if text.isdigit() and len(text) == 18:
        return True
    return False

class PlayerIdValidator(Validator):
    def validate(self, document):
        text = document.text
        if not validate_player_id(text):
            raise ValidationError(message='Please enter a valid 18-digit Discord ID')

def process_csv(file_path, all_users):
    player_mappings = {}
    matches = []
    dummy_id = "000000000000000000"  # Dummy player ID

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row if present
        
        for row in reader:
            match = []
            for player in row[:6]:  # Process all 6 players
                player = player.strip()
                if player in player_mappings:
                    match.append(player_mappings[player])
                elif validate_player_id(player):
                    match.append(int(player))
                    player_mappings[player] = int(player)
                else:
                    closest_match, ratio = find_closest_match(player, all_users)
                    if ratio == 100:
                        match.append(int(closest_match['id']))
                        player_mappings[player] = int(closest_match['id'])
                    else:
                        print(f"\nNo exact match found for '{player}'.")
                        print(f"Closest match: {closest_match['display_name']} (ID: {closest_match['id']})")
                        confirmation = prompt(f"Accept this match? (y/n/i for ignore): ").lower()
                        if confirmation == 'y':
                            match.append(int(closest_match['id']))
                            player_mappings[player] = int(closest_match['id'])
                        elif confirmation == 'i':
                            print(f"Ignoring player '{player}' and using dummy player.")
                            match.append(dummy_id)
                            player_mappings[player] = dummy_id
                        else:
                            manual_id = prompt("Enter the correct Discord ID: ", validator=PlayerIdValidator())
                            match.append(int(manual_id))
                            player_mappings[player] = int(manual_id)
            
            match.extend([int(row[6]), int(row[7])])  # Add scores
            matches.append(match)
    
    return matches

def submit_match(red_alliance, blue_alliance, red_score, blue_score, game_mode_code):
    url = f"{API_BASE_URL}/api/ranked/{game_mode_code}/match/"
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
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error submitting match: Status code {response.status_code}")
        print(f"Response content: {response.text}")
        return None

if __name__ == "__main__":
    csv_file_path = "matches.csv"  # Replace with your CSV file path
    game_mode_code = "CR3v3"  # Replace with the appropriate game mode code
    
    all_users = get_all_users()
    if not all_users:
        print("Failed to fetch users. Exiting.")
        exit(1)
    
    print(f"Fetched {len(all_users)} valid users")
    
    matches = process_csv(csv_file_path, all_users)
    
    print("\nAll players processed. Ready to submit matches.")
    confirmation = prompt("Do you want to submit these matches? (y/n): ").lower()
    
    if confirmation == 'y':
        for match in matches:
            red_alliance = match[:3]
            blue_alliance = match[3:6]
            red_score, blue_score = match[6:]
            result = submit_match(red_alliance, blue_alliance, red_score, blue_score, game_mode_code)
            if result:
                print(f"Match submitted successfully: {result}")
            else:
                print("Failed to submit match. Please check the error message above.")
    else:
        print("Match submission cancelled.")