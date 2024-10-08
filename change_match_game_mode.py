import requests
import os
from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError

# Load environment variables
load_dotenv()

API_KEY = os.getenv('SRC_API_TOKEN')
API_BASE_URL = 'https://secondrobotics.org'

class GameModeValidator(Validator):
    def validate(self, document):
        text = document.text
        if not text:
            raise ValidationError(message='Please enter a valid game mode')

class MatchRangeValidator(Validator):
    def validate(self, document):
        text = document.text
        try:
            start, end = map(int, text.split('-'))
            if start > end:
                raise ValidationError(message='Start match number should be less than or equal to end match number')
        except ValueError:
            raise ValidationError(message='Please enter a valid range (e.g., 1-5)')

def change_match_game_modes(matches):
    url = f"{API_BASE_URL}/api/ranked/change-match-game-modes/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    payload = {"matches": matches}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error changing match game modes: Status code {response.status_code}")
        print(f"Response content: {response.text}")
        return None
    
if __name__ == "__main__":
    new_mode = prompt("Enter the new game mode: ", validator=GameModeValidator())
    match_range = prompt("Enter the range of matches to change (e.g., 1-5): ", validator=MatchRangeValidator())
    
    start_match, end_match = map(int, match_range.split('-'))
    matches = [{"new_game_mode": new_mode, "match_number": i} for i in range(start_match, end_match + 1)]
    
    print("\nReady to change game modes for matches.")
    print(f"Changing matches {start_match} to {end_match} to {new_mode}")
    confirmation = prompt("Do you want to proceed with these changes? (y/n): ").lower()

    if confirmation == 'y':
        results = change_match_game_modes(matches)
        if results:
            for result in results:
                # Add a print statement to inspect the result
                print("Result:", result)
                if 'error' in result:
                    print(f"Failed to update match: {result['error']}")
                else:
                    # Modify this line
                    # print(f"Successfully updated match {result['match_number']} to {new_mode}")
                    match_number = result.get('match', {}).get('match_number')
                    if match_number:
                        print(f"Successfully updated match {match_number} to {new_mode}")
                    else:
                        print("match_number not found in the result.")
        else:
            print("Failed to change match game modes. Please check the error message above.")
    else:
        print("Game mode changes cancelled.")