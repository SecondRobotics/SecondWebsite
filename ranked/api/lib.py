from django.utils import timezone
import math
from rest_framework.response import Response
from typing import List
from discordoauth2.models import User
from ranked.models import EloHistory, GameMode, Match, PlayerElo
from .elo_constants import N, K_BY_SIZE, SCORE_WEIGHT_BY_SIZE, NEW_PLAYER_MULT, EXP_GAMES_BY_SIZE, ELO_FLOOR


# In-memory Welford stats: {game_mode_id: [count, mean, m2]}
# Lazy-loaded from Match history on first access per game mode.
_margin_stats: dict = {}


def _load_margin_stats(game_mode_id: int) -> list:
    """Compute Welford stats from all historical matches for this game mode."""
    count, mean, m2 = 0, 0.0, 0.0
    for match in Match.objects.filter(game_mode_id=game_mode_id).only("red_score", "blue_score"):
        total = match.red_score + match.blue_score
        if total == 0:
            continue
        margin = abs(match.red_score - match.blue_score) / total
        count += 1
        delta = margin - mean
        mean += delta / count
        delta2 = margin - mean
        m2 += delta * delta2
    return [count, mean, m2]


def _update_margin_stats(game_mode_id: int, margin: float) -> None:
    stats = _margin_stats[game_mode_id]
    stats[0] += 1
    delta = margin - stats[1]
    stats[1] += delta / stats[0]
    stats[2] += delta * (margin - stats[1])


def _margin_percentile(game_mode_id: int, margin: float) -> float:
    """
    Returns a value in [0, 1] representing how dominant this margin is
    vs historical margins for this game mode.
    Sigmoid of z-score: 0.5 at an average margin, approaches 1 for a blowout.
    Falls back to raw normalised margin until 10 matches exist.
    """
    if game_mode_id not in _margin_stats:
        _margin_stats[game_mode_id] = _load_margin_stats(game_mode_id)
    count, mean, m2 = _margin_stats[game_mode_id]
    if count < 10:
        return margin
    variance = m2 / count
    if variance <= 0:
        return margin
    z = (margin - mean) / math.sqrt(variance)
    return 1 / (1 + math.exp(-z))


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
    """
    Updates the ELO ratings for players in a match.

    Args:
        match (Match): The match instance.
        red_player_elos (List[PlayerElo]): List of PlayerElo objects for the red alliance.
        blue_player_elos (List[PlayerElo]): List of PlayerElo objects for the blue alliance.

    Returns:
        Tuple[List[float], List[float]]: ELO changes for red and blue alliances.
    """
    n = match.game_mode.players_per_alliance

    # Average ELO per side so win probability is not inflated by team size.
    red_elo = sum(p.elo for p in red_player_elos) / n
    blue_elo = sum(p.elo for p in blue_player_elos) / n

    red_odds = 1 / (1 + 10 ** ((blue_elo - red_elo) / N))
    blue_odds = 1 - red_odds

    k = K_BY_SIZE[n]
    score_weight = SCORE_WEIGHT_BY_SIZE[n]
    exp_games = EXP_GAMES_BY_SIZE[n]

    total_score = match.red_score + match.blue_score

    raw_margin = abs(match.red_score - match.blue_score) / total_score if total_score > 0 else 0
    score_percentile = _margin_percentile(match.game_mode_id, raw_margin)
    _update_margin_stats(match.game_mode_id, raw_margin)

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
            odds = red_odds
            player.total_score += match.red_score
        else:
            score_diff = match.blue_score - match.red_score
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

        # Score bonus: 0 for average margin, up to score_weight for a historically large blowout.
        score_component = score_weight * math.log(3 * score_percentile + 1, 4)

        # Experience multiplier: NEW_PLAYER_MULT for new players, decays toward 1.0.
        experience_mult = 1 + (NEW_PLAYER_MULT - 1) * math.exp(-num_played / exp_games)

        elo_change = (k + score_component) * odds_diff * experience_mult

        elo_changes.append(elo_change)
        player.elo = max(ELO_FLOOR, player.elo + elo_change)
        player.matches_played += 1
        player.last_match_played_time = match.time
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
