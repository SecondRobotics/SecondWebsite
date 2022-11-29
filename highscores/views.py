from typing import Callable, Optional, Type
from discordoauth2.models import User
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max

from .lib import extract_form_data, submit_infinite_recharge, submit_rapid_react, submit_freight_frenzy, submit_spin_up, submit_tipping_point
from .models import Leaderboard, Score
from .forms import ScoreForm, FFScoreForm, IRScoreForm, RRScoreForm, SUScoreForm, TPScoreForm

COMBINED_LEADERBOARD_PAGE = "highscores/combined_leaderboard.html"
SUBMIT_PAGE = "highscores/submit.html"
SUBMIT_ACCEPTED_PAGE = "highscores/submit_accepted.html"
SUBMIT_ERROR_PAGE = "highscores/submit_error.html"


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


def leaderboard_index(request: HttpRequest, name: str) -> HttpResponse:
    if not Leaderboard.objects.filter(name=name).exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    sorted_board = Score.objects.filter(
        leaderboard__name=name, approved=True).order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted_board:
        context.append([i, item])
        i += 1

    return render(request, "highscores/leaderboard_ranks.html", {"ls": context, "robot_name": name})


def leaderboard_combined(request: HttpRequest, game_name: str) -> HttpResponse:
    scores = Score.objects.filter(leaderboard__game=game_name, approved=True).values(
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


def infinite_recharge_combined(request: HttpRequest) -> HttpResponse:
    return leaderboard_combined(request, "Infinite Recharge")


def rapid_react_combined(request: HttpRequest) -> HttpResponse:
    return leaderboard_combined(request, "Rapid React")


def freight_frenzy_combined(request: HttpRequest) -> HttpResponse:
    return leaderboard_combined(request, "Freight Frenzy")


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
def infinite_recharge_submit_form(request: HttpRequest) -> HttpResponse:
    return submit_form_view(request, IRScoreForm, submit_infinite_recharge)


@login_required(login_url='/login')
def rapid_react_submit_form(request: HttpRequest) -> HttpResponse:
    return submit_form_view(request, RRScoreForm, submit_rapid_react)


@login_required(login_url='/login')
def freight_frenzy_submit_form(request: HttpRequest) -> HttpResponse:
    return submit_form_view(request, FFScoreForm, submit_freight_frenzy)


@login_required(login_url='/login')
def tipping_point_submit_form(request: HttpRequest) -> HttpResponse:
    return submit_form_view(request, TPScoreForm, submit_tipping_point)


@login_required(login_url='/login')
def spin_up_submit_form(request: HttpRequest) -> HttpResponse:
    return submit_form_view(request, SUScoreForm, submit_spin_up)
