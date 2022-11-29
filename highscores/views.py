from discordoauth2.models import User
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max

from .lib import extract_form_data, submit_infinite_recharge, submit_rapid_react, submit_freight_frenzy, submit_spin_up, submit_tipping_point
from .models import Leaderboard, Score
from .forms import FFScoreForm, IRScoreForm, RRScoreForm, SUScoreForm, TPScoreForm

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


def infinite_recharge_combined(request: HttpRequest) -> HttpResponse:
    scores = Score.objects.filter(leaderboard__game="Infinite Recharge", approved=True).values(
        'player').annotate(time_set=Max('time_set')).annotate(score=Sum('score'))
    sorted_board = scores.order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted_board:
        item['player'] = User.objects.filter(id=item['player'])[0]
        context.append([i, item])
        i += 1

    return render(request, COMBINED_LEADERBOARD_PAGE, {"ls": context, "game_name": "Infinite Recharge"})


def rapid_react_combined(request: HttpRequest) -> HttpResponse:
    scores = Score.objects.filter(leaderboard__game="Rapid React", approved=True).values(
        'player').annotate(time_set=Max('time_set')).annotate(score=Sum('score'))
    sorted_board = scores.order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted_board:
        item['player'] = User.objects.filter(id=item['player'])[0]
        context.append([i, item])
        i += 1

    return render(request, COMBINED_LEADERBOARD_PAGE, {"ls": context, "game_name": "Rapid React"})


def freight_frenzy_combined(request: HttpRequest) -> HttpResponse:
    scores = Score.objects.filter(leaderboard__game="Freight Frenzy", approved=True).values(
        'player').annotate(time_set=Max('time_set')).annotate(score=Sum('score'))
    sorted_board = scores.order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted_board:
        item['player'] = User.objects.filter(id=item['player'])[0]
        context.append([i, item])
        i += 1

    return render(request, COMBINED_LEADERBOARD_PAGE, {"ls": context, "game_name": "Freight Frenzy"})


@login_required(login_url='/login')
def infinite_recharge_submit_form(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": IRScoreForm})

    form = IRScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    res = submit_infinite_recharge(score_obj)
    if (res is not None):
        return error_response(request, res)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def rapid_react_submit_form(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": RRScoreForm})

    form = RRScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    res = submit_rapid_react(score_obj)
    if (res is not None):
        return error_response(request, res)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def freight_frenzy_submit_form(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": FFScoreForm})

    form = FFScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    res = submit_freight_frenzy(score_obj)
    if (res is not None):
        return error_response(request, res)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def tipping_point_submit_form(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": TPScoreForm})

    form = TPScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    res = submit_tipping_point(score_obj)
    if (res is not None):
        return error_response(request, res)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def spin_up_submit_form(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": SUScoreForm})

    form = SUScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    res = submit_spin_up(score_obj)
    if (res is not None):
        return error_response(request, res)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})
