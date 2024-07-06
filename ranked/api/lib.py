from django.utils import timezone
import math
from rest_framework.response import Response
from typing import List
from discordoauth2.models import User
from ranked.models import EloHistory, GameMode, Match, PlayerElo
from .elo_constants import N, K, R, B, C, D, A


def validate_post_match_req_body(body: dict, players_per_alliance: int):
    if body is None or 'red_alliance' not in body or 'blue_alliance' not in body or \
            'red_score' not in body or 'blue_score' not in body:
        return Response(status=400, data={
            'error': 'Missing required fields in request body.'
        })

    if not isinstance(body['red_alliance'], list) or not isinstance(body['blue_alliance'], list):
        return Response(status=400, data={
            'error': 'red_alliance and blue_alliance must be arrays.'
        })

    if len(body['red_alliance']) != players_per_alliance or len(body['blue_alliance']) != players_per_alliance:
        return Response(status=400, data={
            'error': 'Invalid number of players per alliance.'
        })

    if not isinstance(body['red_score'], int) or not isinstance(body['blue_score'], int):
        return Response(status=400, data={
            'error': 'Score must be integers.'
        })

    if body['red_score'] < 0 or body['blue_score'] < 0:
        return Response(status=400, data={
            'error': 'Score cannot be negative.'
        })

    return None


def validate_patch_match_req_body(body: dict):
    if body is None or 'red_score' not in body or 'blue_score' not in body:
        return Response(status=400, data={
            'error': 'Missing required fields in request body.'
        })

    if not isinstance(body['red_score'], int) or not isinstance(body['blue_score'], int):
        return Response(status=400, data={
            'error': 'Score must be integers.'
        })

    if body['red_score'] < 0 or body['blue_score'] < 0:
        return Response(status=400, data={
            'error': 'Score cannot be negative.'
        })

    return None


def get_match_player_info(red_alliance: List[User], blue_alliance: List[User], game_mode: GameMode):
    # Get players
    red_players = []
    for player_id in red_alliance:
        try:
            player = User.objects.get(id=player_id)
        except User.DoesNotExist:
            return Response(status=404, data={
                'error': f'Player {player_id} does not exist.'
            }), None, None, None, None
        red_players.append(player)
    blue_players = []
    for player_id in blue_alliance:
        try:
            player = User.objects.get(id=player_id)
        except User.DoesNotExist:
            return Response(status=404, data={
                'error': f'Player {player_id} does not exist.'
            }), None, None, None, None
        blue_players.append(player)

    # Get player elos
    red_player_elos = []
    for player in red_players:
        player_elo = PlayerElo.objects.get_or_create(
            player=player, game_mode=game_mode)[0]
        red_player_elos.append(player_elo)
    blue_player_elos = []
    for player in blue_players:
        player_elo = PlayerElo.objects.get_or_create(
            player=player, game_mode=game_mode)[0]
        blue_player_elos.append(player_elo)

    return None, red_players, blue_players, red_player_elos, blue_player_elos


def update_player_elos(match: Match, red_player_elos: List[PlayerElo], blue_player_elos: List[PlayerElo]):
    red_elo = match.red_starting_elo
    blue_elo = match.blue_starting_elo

    red_odds = 1 / (1 + 10 ** ((blue_elo - red_elo) / N))
    blue_odds = 1 / (1 + 10 ** ((red_elo - blue_elo) / N))

    elo_changes = []

    for player in red_player_elos + blue_player_elos:
        num_played = player.matches_played

        EloHistory.objects.create(
            player_elo=player,
            match_number=match.match_number,
            elo=player.elo,
        )

        if player in red_player_elos:
            score_diff = match.red_score - match.blue_score
            relative_score_diff = abs(score_diff) / (match.red_score + match.blue_score)
            odds = red_odds
            player.total_score += match.red_score
        else:
            score_diff = match.blue_score - match.red_score
            relative_score_diff = abs(score_diff) / (match.red_score + match.blue_score)
            odds = blue_odds
            player.total_score += match.blue_score

        if score_diff > 0:
            odds_diff = 1 - odds
            player.matches_won += 1
        elif score_diff == 0:
            odds_diff = 0.5 - odds
            player.matches_drawn += 1
        else:
            odds_diff = 0 - odds
            player.matches_lost += 1

        # Increase the importance of the score difference
        importance_factor = 1.5
        adjusted_score_diff = importance_factor * relative_score_diff

        elo_change = ((
            K / (1 + 0) + 2 * math.log(adjusted_score_diff + 1, 8)) * (
            odds_diff)) * (((B - 1) / (A ** num_played)) + 1)


        elo_changes.append(elo_change)
        player.elo += elo_change

        player.matches_played += 1
        player.last_match_played_time = timezone.now()
        player.last_match_played_number = match.match_number

        player.save()

    red_elo_changes = elo_changes[:len(red_player_elos)]
    blue_elo_changes = elo_changes[len(red_player_elos):]

    return red_elo_changes, blue_elo_changes


def revert_player_elos(match: Match, red_elo_history: List[EloHistory], blue_elo_history: List[EloHistory]):
    # Revert the elo on PlayerElo to the elo on EloHistory
    for elo_history_entry in red_elo_history:
        elo_history_entry.player_elo.elo = elo_history_entry.elo
        elo_history_entry.player_elo.matches_played -= 1
        elo_history_entry.player_elo.total_score -= match.red_score

        if match.red_score > match.blue_score:
            elo_history_entry.player_elo.matches_won -= 1
        elif match.red_score < match.blue_score:
            elo_history_entry.player_elo.matches_lost -= 1
        else:
            elo_history_entry.player_elo.matches_drawn -= 1

        elo_history_entry.player_elo.save()
        elo_history_entry.delete()

    for elo_history_entry in blue_elo_history:
        elo_history_entry.player_elo.elo = elo_history_entry.elo
        elo_history_entry.player_elo.matches_played -= 1
        elo_history_entry.player_elo.total_score -= match.blue_score

        if match.red_score < match.blue_score:
            elo_history_entry.player_elo.matches_won -= 1
        elif match.red_score > match.blue_score:
            elo_history_entry.player_elo.matches_lost -= 1
        else:
            elo_history_entry.player_elo.matches_drawn -= 1

        elo_history_entry.player_elo.save()
        elo_history_entry.delete()
