from typing import Callable, Optional, Type
from discordoauth2.models import User
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max

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
            world_records.append(highest_score)

    # Sort the world records by the date they were set
    world_records.sort(key=lambda x: x.time_set)

    return render(request, WR_PAGE, {"world_records": world_records})


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
