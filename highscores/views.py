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

    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted_board:
        context.append([i, item])
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
        days, _ = divmod(remainder, 86400)  # 60*60*24

        record.active_for = f"{int(years)} years, {int(months)} months, {int(days)} days"

    # Count the number of records per player
    player_counts = Counter(record.player.username for record in world_records)
    player_counts = sorted(player_counts.items(), key=lambda x: x[1], reverse=True)

    return render(request, WR_PAGE, {"world_records": world_records, "player_counts": player_counts})


def leaderboard_combined(request: HttpRequest, game_slug: str) -> HttpResponse:
    if not Leaderboard.objects.filter(game_slug=game_slug).exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    game_name = Leaderboard.objects.filter(game_slug=game_slug)[0].game

    scores = Score.objects.filter(leaderboard__game_slug=game_slug, approved=True).values(
        'player').annotate(time_set=Max('time_set')).annotate(score=Sum('score'))
    sorted_board = scores.order_by('-score', 'time_set')

    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted_board:
        item['player'] = User.objects.filter(id=item['player'])[0]
        context.append([i, item])
        i += 1

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


@login_required(login_url='/login')
def submit_form(request: HttpRequest, game_slug: str) -> HttpResponse:
    return submit_form_view(request, get_score_form(game_slug), game_slug_to_submit_func[game_slug])
