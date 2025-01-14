import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('SRC_API_TOKEN')
API_BASE_URL = 'https://secondrobotics.org'

def clear_leaderboard(game_mode):
    url = f"{API_BASE_URL}/api/ranked/clear-leaderboard/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    payload = {"game_mode": game_mode}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Leaderboard cleared successfully.")
    else:
        print(f"Error clearing leaderboard: Status code {response.status_code}")
        print(f"Response content: {response.text}")

def recalculate_elo(game_mode):
    url = f"{API_BASE_URL}/api/ranked/recalculate-elo/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    payload = {"game_mode": game_mode}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("ELO recalculated successfully.")
    else:
        print(f"Error recalculating ELO: Status code {response.status_code}")
        print(f"Response content: {response.text}")

if __name__ == "__main__":
    game_mode = input("Enter the game mode to reset and recalculate ELO: ")
    
    confirmation = input(f"Are you sure you want to clear the leaderboard and recalculate ELO for game mode '{game_mode}'? (y/n): ").lower()
    
    if confirmation == 'y':
        clear_leaderboard(game_mode)
        recalculate_elo(game_mode)
    else:
        print("Operation cancelled.")