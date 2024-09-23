from django.shortcuts import render, HttpResponseRedirect
from django.db.models import Max, Min, F, Q, Count, ExpressionWrapper, FloatField, Case, When, Value, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import math

from .models import EloHistory, GameMode, PlayerElo
from .templatetags.rank_filter import mmr_to_rank
from django.db.models.functions import Exp

# Create your views here.

def ranked_home(request):
    game_modes = GameMode.objects.annotate(
        match_count=Count(
            'match',
            filter=Q(match__time__gte=timezone.now() - timedelta(days=7))
        )
    ).order_by('-match_count')

    # Create a dictionary mapping game name to array of game modes
    game_dict = {}
    for game_mode in game_modes:
        if game_mode.game not in game_dict:
            game_dict[game_mode.game] = []
        game_dict[game_mode.game].append(game_mode)

    context = {'games': game_dict}
    return render(request, 'ranked/ranked_home.html', context)

def leaderboard(request, name):
    gamemode = GameMode.objects.filter(short_code=name)

    if not gamemode.exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ranked'))

    gamemode = gamemode[0]

    players = PlayerElo.objects.filter(game_mode=gamemode, matches_played__gt=20)
    players = players.annotate(
        time_delta=ExpressionWrapper(
            datetime.now(timezone.utc) - F('last_match_played_time'),
            output_field=FloatField()
        ) / 3600000000
    )

    players = players.annotate(
        mmr = ExpressionWrapper(
            Case(
                # When time_delta > 168
                When(
                    time_delta__gt=168,
                    then=ExpressionWrapper(
                        150 * Exp(-0.00175 * (F('time_delta') - Value(168))) + F('elo') - 150,
                        output_field=FloatField()
                    )
                ),
                # When time_delta <= 168
                When(
                    time_delta__lte=168,
                    then=F('elo')
                ),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    )


    # Get highest and lowest MMR values
    highest_mmr = players.aggregate(Max('mmr'))['mmr__max']
    lowest_mmr = players.aggregate(Min('mmr'))['mmr__min']

    players_with_rank = []
    for player in players:
        rank, color = mmr_to_rank(player.mmr, highest_mmr, lowest_mmr)
        players_with_rank.append({
            'player': player,
            'rank': rank,
            'color': color,
        })

    # Sort players_with_rank by MMR in descending order
    players_with_rank = sorted(players_with_rank, key=lambda x: x['player'].mmr, reverse=True)

    context = {
        'leaderboard_code': gamemode.short_code,
        'leaderboard_name': gamemode.name,
        'players_with_rank': players_with_rank,
    }

    return render(request, "ranked/leaderboard.html", context)

def player_info(request, name, player_id):
    if not player_id.isdigit():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ranked'))

    player_info = PlayerElo.objects.filter(
        game_mode__short_code=name, player__id=player_id)

    if not player_info.exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ranked'))

    player = player_info[0]

    mmr = round(mmr_calc(player.elo, player.matches_played, (datetime.now(timezone.utc) - player.last_match_played_time).total_seconds()/3600), 1)

    elo_history = EloHistory.objects.filter(player_elo=player)
    match_labels = [eh.match_number for eh in elo_history]
    elo_history = [eh.elo for eh in elo_history]

    context = {'player': player, 'mmr': mmr,
               'elo_history': elo_history, 'match_labels': match_labels}
    return render(request, 'ranked/player_info.html', context)

def mmr_calc(elo, matches_played, delta_hours):
    return elo * 2 / ((1 + pow(math.e, 1/168 * pow(delta_hours, 0.63))) * (1 + pow(math.e, -0.33 * matches_played)))

def global_leaderboard(request):
    # Annotate each game type with the total number of matches across all players
    total_matches_per_game = GameMode.objects.values('game').annotate(total_matches=Count('match'))
    game_to_total_matches = {item['game']: item['total_matches'] for item in total_matches_per_game}

    if not game_to_total_matches:
        context = {
            'leaderboard_code': 'global',
            'leaderboard_name': 'Global Elo Leaderboard',
            'players_with_rank': [],
        }
        return render(request, "ranked/global_leaderboard.html", context)

    max_total_matches = max(game_to_total_matches.values())

    # Calculate scaling factors based on total matches per game type
    scaling_factors = {
        game: (matches / max_total_matches) * (2/3) + (1/3)
        for game, matches in game_to_total_matches.items()
    }

    # Fetch all players
    players = PlayerElo.objects.all()

    global_scores = []

    for player in players:
        # Corrected the filter to use the related User instance
        player_game_elos = PlayerElo.objects.filter(player=player.player).select_related('game_mode')

        if not player_game_elos.exists():
            continue

        # Determine the most played game mode per game type for the player
        game_type_dict = {}
        for player_game_elo in player_game_elos:
            game_type = player_game_elo.game_mode.game
            match_count = player_game_elo.matches_played
            mode = player_game_elo.game_mode
            if (
                game_type not in game_type_dict or
                match_count > game_type_dict[game_type]['match_count']
            ):
                # Include the player's elo in the game_type_dict
                game_type_dict[game_type] = {
                    'mode': mode,
                    'match_count': match_count,
                    'elo': player_game_elo.elo  # Added 'elo' here
                }

        # Calculate weighted Elo based on scaling factors
        total_weight = 0
        weighted_elo = 0
        for game_type, data in game_type_dict.items():
            scaling_factor = scaling_factors.get(game_type, 1/3)  # Default to minimum weight
            weighted_elo += data['elo'] * scaling_factor
            total_weight += scaling_factor

        if total_weight > 0:
            global_elo = weighted_elo / total_weight
            global_scores.append({'player': player, 'global_elo': global_elo})

    # Sort players by global Elo in descending order
    global_scores = sorted(global_scores, key=lambda x: x['global_elo'], reverse=True)

    # Assign ranks and colors
    highest_elo = global_scores[0]['global_elo'] if global_scores else 0
    lowest_elo = global_scores[-1]['global_elo'] if global_scores else 0

    players_with_rank = []
    for entry in global_scores:
        rank, color = mmr_to_rank(entry['global_elo'], highest_elo, lowest_elo)
        players_with_rank.append({
            'player': entry['player'],
            'rank': rank,
            'color': color,
            'global_elo': round(entry['global_elo'], 1),
        })

    context = {
        'leaderboard_code': 'global',
        'leaderboard_name': 'Global Elo Leaderboard',
        'players_with_rank': players_with_rank,
    }

    return render(request, "ranked/global_leaderboard.html", context)
