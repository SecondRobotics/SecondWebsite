from django.shortcuts import render
from django.http.response import HttpResponseRedirect
from django.db.models import Max, Min, F
from django.db.models import Q, Count
from django.db.models import IntegerField, ExpressionWrapper, FloatField
from django.db.models.functions import ExtractHour
from django.utils import timezone
from datetime import timedelta, datetime, tzinfo
import math

from .models import EloHistory, GameMode, PlayerElo, Match

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

    players = PlayerElo.objects.filter(game_mode=gamemode)

    players = players.annotate(time_delta=ExpressionWrapper(datetime.now(timezone.utc) - F('last_match_played_time'), output_field=FloatField()) / 3600000000)

    # Calculate MMR
    players = players.annotate(mmr=mmr_calc(F('elo'), F('matches_played'), F('time_delta')))

    # Get highest and lowest MMR values
    highest_mmr = players.aggregate(Max('mmr'))['mmr__max']
    lowest_mmr = players.aggregate(Min('mmr'))['mmr__min']

    players = players.order_by('-mmr')

    context = {
        'leaderboard_code': gamemode.short_code,
        'leaderboard_name': gamemode.name,
        'players': players,
        'highest_mmr': highest_mmr,
        'lowest_mmr': lowest_mmr
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