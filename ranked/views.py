from django.shortcuts import render, HttpResponseRedirect
from django.db.models import Max, Min, F, Q, Count, ExpressionWrapper, FloatField, Case, When, Value
from django.utils import timezone
from datetime import datetime, timedelta
import math

from .models import EloHistory, GameMode, PlayerElo, Match
from .templatetags.rank_filter import mmr_to_rank
from django.db.models.functions import Exp
from discordoauth2.models import User

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

    # Get all matches for the player
    matches = Match.objects.filter(
        Q(red_alliance=player.player) | Q(blue_alliance=player.player),
        game_mode=player.game_mode
    )

    # Players Played With
    players_with = User.objects.filter(
        Q(red_alliance__in=matches.filter(red_alliance=player.player)) |
        Q(blue_alliance__in=matches.filter(blue_alliance=player.player))
    ).exclude(id=player.player.id).distinct()

    players_with_stats = []
    for played_with in players_with:
        matches_together = matches.filter(
            Q(red_alliance=player.player, red_alliance=played_with) |
            Q(blue_alliance=player.player, blue_alliance=played_with)
        )
        total_matches = matches_together.count()
        wins = matches_together.filter(
            Q(red_alliance=player.player, red_alliance=played_with, winner='red') |
            Q(blue_alliance=player.player, blue_alliance=played_with, winner='blue')
        ).count()
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        players_with_stats.append({
            'player__username': played_with.username,
            'total_matches': total_matches,
            'win_rate': win_rate
        })

    players_with_stats = sorted(players_with_stats, key=lambda x: (-x['win_rate'], -x['total_matches']))

    # Players Played Against
    players_against = User.objects.filter(
        Q(red_alliance__in=matches.filter(blue_alliance=player.player)) |
        Q(blue_alliance__in=matches.filter(red_alliance=player.player))
    ).distinct()

    players_against_stats = []
    for played_against in players_against:
        matches_against = matches.filter(
            Q(red_alliance=player.player, blue_alliance=played_against) |
            Q(blue_alliance=player.player, red_alliance=played_against)
        )
        total_matches = matches_against.count()
        wins = matches_against.filter(
            Q(red_alliance=player.player, winner='red') |
            Q(blue_alliance=player.player, winner='blue')
        ).count()
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        players_against_stats.append({
            'player__username': played_against.username,
            'total_matches': total_matches,
            'win_rate': win_rate
        })

    players_against_stats = sorted(players_against_stats, key=lambda x: (-x['win_rate'], -x['total_matches']))

    context = {
        'player': player,
        'mmr': mmr,
        'elo_history': elo_history,
        'match_labels': match_labels,
        'players_with': players_with_stats,
        'players_against': players_against_stats,
    }
    return render(request, 'ranked/player_info.html', context)

def mmr_calc(elo, matches_played, delta_hours):
    return elo * 2 / ((1 + pow(math.e, 1/168 * pow(delta_hours, 0.63))) * (1 + pow(math.e, -0.33 * matches_played)))
