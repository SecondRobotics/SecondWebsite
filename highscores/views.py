from typing import Callable, Optional, Type
from discordoauth2.models import User
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max
from django.utils.timezone import make_aware
from datetime import datetime
from collections import Counter
from django.db.models import Sum, Max, F, Count, Prefetch
from django.db.models.functions import Coalesce
from django.core.cache import cache

from .lib import extract_form_data, game_slug_to_submit_func
from .models import Leaderboard, Score
from .forms import ScoreForm, get_score_form

COMBINED_LEADERBOARD_PAGE = "highscores/combined_leaderboard.html"
SUBMIT_PAGE = "highscores/submit.html"
SUBMIT_ACCEPTED_PAGE = "highscores/submit_accepted.html"
SUBMIT_ERROR_PAGE = "highscores/submit_error.html"
WR_PAGE = "highscores/world_records.html"


def home(request: HttpRequest) -> HttpResponse:
    leaderboards = Leaderboard.objects.all().order_by('-id')

    # Create a dictionary mapping game name to array of leaderboards
    leaderboards_dict = {}
    for leaderboard in leaderboards:
        game = leaderboard.game
        if game not in leaderboards_dict:
            leaderboards_dict[game] = []
        leaderboards_dict[leaderboard.game].append(leaderboard)

    return render(request, "highscores/highscore_home.html", {"games": leaderboards_dict})


def error_response(request: HttpRequest, error_message: str) -> HttpResponse:
    return render(request, SUBMIT_ERROR_PAGE, {'error': error_message})


def leaderboard_robot(request: HttpRequest, game_slug: str, name: str) -> HttpResponse:
    if not Leaderboard.objects.filter(game_slug=game_slug, name=name).exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    sorted_board = Score.objects.filter(
        leaderboard__game_slug=game_slug, leaderboard__name=name, approved=True).order_by('-score', 'time_set')

    # Find the highest score (world record)
    if sorted_board.exists():
        highest_score = sorted_board.first().score
    else:
        highest_score = 1  # Avoid division by zero

    i = 1
    context = []
    # Create ranking numbers, calculate percentiles, and append them to sorted values
    for item in sorted_board:
        percentile = (item.score / highest_score) * 100
        context.append([i, item, percentile])
        i += 1

    return render(request, "highscores/leaderboard_ranks.html", {"ls": context, "robot_name": name})


def world_records(request: HttpRequest) -> HttpResponse:
    # Get all leaderboards
    leaderboards = Leaderboard.objects.all()

    # Collect the highest scores for each leaderboard
    world_records = []
    for leaderboard in leaderboards:
        highest_score = Score.objects.filter(leaderboard=leaderboard, approved=True).order_by('-score', 'time_set').first()
        if highest_score:
            highest_score.robot_name = leaderboard.name  # Include robot name
            world_records.append(highest_score)

    # Sort the world records by the date they were set
    world_records.sort(key=lambda x: x.time_set)

    # Calculate how long each record has been active
    now = make_aware(datetime.now())
    for record in world_records:
        time_set = record.time_set
        active_duration = now - time_set

        years, remainder = divmod(active_duration.total_seconds(), 31536000)  # 60*60*24*365
        months, remainder = divmod(remainder, 2592000)  # 60*60*24*30
        days = remainder / 86400  # 60*60*24

        record.active_for = f"{int(years)} years, {int(months)} months, {days:.1f} days"

    # Count the number of records per player
    player_counts = Counter(record.player.username for record in world_records)
    player_counts = sorted(player_counts.items(), key=lambda x: x[1], reverse=True)

    return render(request, WR_PAGE, {"world_records": world_records, "player_counts": player_counts})

def leaderboard_combined(request: HttpRequest, game_slug: str) -> HttpResponse:
    cache_key = f'leaderboard_combined_{game_slug}'
    context = cache.get(cache_key)
    if context:
        return render(request, COMBINED_LEADERBOARD_PAGE, context)

    if not Leaderboard.objects.filter(game_slug=game_slug).exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    game_name = Leaderboard.objects.filter(game_slug=game_slug).first().game
    leaderboards = Leaderboard.objects.filter(game_slug=game_slug)

    # Prefetch related scores for all leaderboards
    scores_prefetch = Prefetch('score_set', queryset=Score.objects.filter(approved=True).select_related('player'))
    leaderboards = leaderboards.prefetch_related(scores_prefetch)

    player_percentiles = {}
    all_players = set()

    for leaderboard in leaderboards:
        scores = leaderboard.score_set.all().order_by('-score', 'time_set')
        if not scores.exists():
            continue
        highest_score = scores.first().score

        for score in scores:
            percentile = (score.score / highest_score) * 100
            if score.player.id not in player_percentiles:
                player_percentiles[score.player.id] = []
            player_percentiles[score.player.id].append(percentile)
            all_players.add(score.player.id)

    # Ensure every player has a score for each leaderboard (0% if missing)
    for player_id in all_players:
        if player_id not in player_percentiles:
            player_percentiles[player_id] = []
        for leaderboard in leaderboards:
            if len(player_percentiles[player_id]) < leaderboards.count():
                player_percentiles[player_id].append(0.0)

    average_percentiles = {player_id: sum(percentiles) / len(percentiles) for player_id, percentiles in player_percentiles.items()}
    sorted_average_percentiles = sorted(average_percentiles.items(), key=lambda x: x[1], reverse=True)

    context = []
    i = 1
    player_objects = User.objects.filter(id__in=all_players).in_bulk()
    for player_id, avg_percentile in sorted_average_percentiles:
        player = player_objects[player_id]
        total_score = Score.objects.filter(player=player, leaderboard__game_slug=game_slug, approved=True).aggregate(total_score=Sum('score'))['total_score']
        last_time_set = Score.objects.filter(player=player, leaderboard__game_slug=game_slug, approved=True).aggregate(last_time_set=Max('time_set'))['last_time_set']
        context.append([i, {'player': player, 'average_percentile': avg_percentile, 'score': total_score, 'time_set': last_time_set}])
        i += 1

    cache.set(cache_key, {"ls": context, "game_name": game_name}, 300)  # Cache for 5 minutes
    return render(request, COMBINED_LEADERBOARD_PAGE, {"ls": context, "game_name": game_name})


def submit_form_view(request: HttpRequest, form_class: Type[ScoreForm], submit_func: Callable[[Score], Optional[str]]) -> HttpResponse:
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": form_class})

    form = form_class(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    res = submit_func(score_obj)
    if (res is not None):
        return error_response(request, res)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})

def overall_singleplayer_leaderboard(request: HttpRequest) -> HttpResponse:
    cache_key = 'overall_singleplayer_leaderboard'
    context = cache.get(cache_key)
    if context:
        return render(request, "highscores/overall_singleplayer_leaderboard.html", context)

    leaderboards = Leaderboard.objects.all()

    # Prefetch related scores for all leaderboards
    scores_prefetch = Prefetch('score_set', queryset=Score.objects.filter(approved=True).select_related('player'))
    leaderboards = leaderboards.prefetch_related(scores_prefetch)

    player_percentiles = {}
    all_players = set()

    for leaderboard in leaderboards:
        scores = leaderboard.score_set.all().order_by('-score', 'time_set')
        if not scores.exists():
            continue
        highest_score = scores.first().score

        for score in scores:
            percentile = (score.score / highest_score) * 100
            if score.player.id not in player_percentiles:
                player_percentiles[score.player.id] = []
            player_percentiles[score.player.id].append(percentile)
            all_players.add(score.player.id)

    # Ensure every player has a score for each leaderboard (0% if missing)
    for player_id in all_players:
        if player_id not in player_percentiles:
            player_percentiles[player_id] = []
        for leaderboard in leaderboards:
            if len(player_percentiles[player_id]) < leaderboards.count():
                player_percentiles[player_id].append(0.0)

    average_percentiles = {player_id: sum(percentiles) / len(percentiles) for player_id, percentiles in player_percentiles.items()}
    sorted_average_percentiles = sorted(average_percentiles.items(), key=lambda x: x[1], reverse=True)

    context = []
    i = 1
    player_objects = User.objects.filter(id__in=all_players).in_bulk()
    for player_id, avg_percentile in sorted_average_percentiles:
        player = player_objects[player_id]
        total_score = Score.objects.filter(player=player, approved=True).aggregate(total_score=Sum('score'))['total_score']
        last_time_set = Score.objects.filter(player=player, approved=True).aggregate(last_time_set=Max('time_set'))['last_time_set']
        context.append([i, {'player': player, 'average_percentile': avg_percentile, 'score': total_score, 'time_set': last_time_set}])
        i += 1

    cache.set(cache_key, {"ls": context}, 300)  # Cache for 5 minutes
    return render(request, "highscores/overall_singleplayer_leaderboard.html", {"ls": context})



@login_required(login_url='/login')
def submit_form(request: HttpRequest, game_slug: str) -> HttpResponse:
    return submit_form_view(request, get_score_form(game_slug), game_slug_to_submit_func[game_slug])
