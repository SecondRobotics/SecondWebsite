from django.shortcuts import render
from django.http.response import HttpResponseRedirect
from django.db.models import Max, F

from .models import GameMode, PlayerElo, Match

# Create your views here.

def ranked_home(request):
    return render(request, "ranked/ranked_home.html")

def leaderboard(request, name):
    gamemode = GameMode.objects.filter(short_code=name)

    if not gamemode.exists():
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ranked'))

    gamemode = gamemode[0]

    players = PlayerElo.objects.filter(game_mode=gamemode)

    max_matches_played = players.aggregate(Max('matches_played'))['matches_played__max']

    most_recent_match = Match.objects.filter(game_mode=gamemode).aggregate(Max('match_number'))['match_number__max']

    # players = players.annotate(mmr=F('elo') - ((most_recent_match - F('last_match_played_number')) * 1.15) + (30 * (F('matches_played') / max_matches_played)))
    players = players.annotate(mmr=F('elo') - ((most_recent_match - F('last_match_played_number')) * 1.15) + (30 * (F('matches_played') / max_matches_played)))

    players = players.order_by('-mmr')

    context = {'leaderboard_code': gamemode.short_code, 'leaderboard_name': gamemode.name, 'players': players}

    return render(request, "ranked/leaderboard.html", context)

def player_info(request, name, player_name):
    player_info = PlayerElo.objects.filter(game_mode__short_code=name, player__username=player_name)

    if not player_info.exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ranked'))
    
    player = player_info[0]

    all_players = PlayerElo.objects.filter(game_mode=player.game_mode)

    max_matches_played = all_players.aggregate(Max('matches_played'))['matches_played__max']

    most_recent_match = Match.objects.filter(game_mode=player.game_mode).aggregate(Max('match_number'))['match_number__max']

    mmr = round(player.elo - ((most_recent_match - player.last_match_played_number) * 1.15) + (30 * (player.matches_played / max_matches_played)), 1)

    context = {'player': player, 'mmr': mmr}
    
    return render(request, 'ranked/player_info.html', context)

