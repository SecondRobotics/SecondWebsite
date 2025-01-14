import math
from datetime import datetime, timedelta

from django.db.models import (Case, Count, ExpressionWrapper, F, FloatField,
                              Max, Min, Q, Value, When)
from django.db.models.functions import Exp
from django.shortcuts import HttpResponseRedirect, render
from django.utils import timezone

from .models import EloHistory, GameMode, PlayerElo
from .templatetags.rank_filter import mmr_to_rank

# Create your views here.


def ranked_home(request):
    game_modes = GameMode.objects.annotate(
        match_count=Count(
            'match',
            filter=Q(match__time__gte=timezone.now() - timedelta(days=7))
        )
    ).order_by('-match_count')  # Order by most matches played in the last 7 days

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

    players = PlayerElo.objects.filter(
        game_mode=gamemode, matches_played__gt=20)
    players = players.annotate(
        time_delta=ExpressionWrapper(
            datetime.now(timezone.utc) - F('last_match_played_time'),
            output_field=FloatField()
        ) / 3600000000
    )

    players = players.annotate(
        mmr=ExpressionWrapper(
            Case(
                # When time_delta > 168
                When(
                    time_delta__gt=168,
                    then=ExpressionWrapper(
                        150 * Exp(-0.00175 * (F('time_delta') - \
                                  Value(168))) + F('elo') - 150,
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
    players_with_rank = sorted(
        players_with_rank, key=lambda x: x['player'].mmr, reverse=True)

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
        game_mode__short_code=name, player__id=player_id
    )

    if not player_info.exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ranked'))

    player = player_info.first()

    # Handle cases where last_match_played_time is None
    if player.last_match_played_time:
        delta_hours = (timezone.now() -
                       player.last_match_played_time).total_seconds() / 3600
    else:
        # Define a default value or handle as needed
        # For example, setting delta_hours to 0 or a specific number
        delta_hours = 0  # Or set to a default like 24 * 7 for a week

    mmr = round(mmr_calc(player.elo, player.matches_played, delta_hours), 1)

    elo_history = EloHistory.objects.filter(player_elo=player)
    match_labels = [eh.match_number for eh in elo_history]
    elo_history = [eh.elo for eh in elo_history]

    context = {'player': player, 'mmr': mmr,
               'elo_history': elo_history, 'match_labels': match_labels}
    return render(request, 'ranked/player_info.html', context)


def mmr_calc(elo, matches_played, delta_hours):
    return elo * 2 / ((1 + pow(math.e, 1/168 * pow(delta_hours, 0.63))) * (1 + pow(math.e, -0.33 * matches_played)))
