from discordoauth2.models import User
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from .models import Leaderboard, Score, CleanCodeSubmission
from datetime import datetime
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max, Q

from .forms import FFScoreForm, IRScoreForm, RRScoreForm, ScoreForm, TPScoreForm
from SRCweb.settings import NEW_AES_KEY, DEBUG

from Crypto.Cipher import AES
from urllib.request import urlopen, Request

# Create your views here.
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'

WRONG_ROBOT_MESSAGE = 'Double-check the robot type that you selected!'
HIGHER_SCORE_MESSAGE = 'You already have a submission with an equal or higher score than this!'
ERROR_WRONG_GAME_MESSAGE = 'There is something wrong with your clean code! Are you submitting for the right game?'
ERROR_CORRUPT_CODE_MESSAGE = 'There is something wrong with your clean code! Make sure you copied it properly.'
BAD_URL_MESSAGE = 'There is something wrong with the URL you provided for your screenshot/video. Please ensure you provide a link to a PNG, JPEG, YouTube video, or Streamable video.'
WRONG_VERSION_MESSAGE = 'Your version of the game is outdated and not supported. Please update to the latest version at https://xrcsimulator.org/downloads/.'
PRERELEASE_MESSAGE = 'Pre-release versions are not allowed for high score submission!'

COMBINED_LEADERBOARD_PAGE = "highscores/combined_leaderboard.html"
SUBMIT_PAGE = "highscores/submit.html"
SUBMIT_ACCEPTED_PAGE = "highscores/submit_accepted.html"
SUBMIT_ERROR_PAGE = "highscores/submit_error.html"


def home(request):
    return render(request, "highscores/highscore_home.html")


def error_response(request, error_message):
    return render(request, SUBMIT_ERROR_PAGE, {'error': error_message})


def leaderboard_index(request, name):
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


def infinite_recharge_combined(request):
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


def rapid_react_combined(request):
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


def freight_frenzy_combined(request):
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
def infinite_recharge_submit(request):
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": IRScoreForm})

    form = IRScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    # Check for older submissions from this user in this category
    prev_submissions = Score.objects.filter(
        leaderboard__name=score_obj.leaderboard, player=score_obj.player)

    for submission in prev_submissions:
        if submission.score >= score_obj.score:
            return error_response(request, HIGHER_SCORE_MESSAGE)

    # Check to ensure image / video is proper
    res = submission_screenshot_check(score_obj, request)
    if (res is not None):
        return res

    # Check the clean code
    res = infinite_recharge_clean_code_check(score_obj, request)
    if (res is not None):
        return res

    # Code is valid! Instantly approve!
    approve_score(score_obj, prev_submissions)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def rapid_react_submit(request):
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": RRScoreForm})

    form = RRScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    # Check for older submissions from this user in this category
    prev_submissions = Score.objects.filter(
        leaderboard__name=score_obj.leaderboard, player=score_obj.player)

    for submission in prev_submissions:
        if submission.score >= score_obj.score:
            return error_response(request, HIGHER_SCORE_MESSAGE)

    # Check to ensure image / video is proper
    res = submission_screenshot_check(score_obj, request)
    if (res is not None):
        return res

    # Check the clean code
    res = rapid_react_clean_code_check(score_obj, request)
    if (res is not None):
        return res

    # Code is valid! Instantly approve!
    approve_score(score_obj, prev_submissions)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def freight_frenzy_submit(request):
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": FFScoreForm})

    form = FFScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    # Check for older submissions from this user in this category
    prev_submissions = Score.objects.filter(
        leaderboard__name=score_obj.leaderboard, player=score_obj.player)

    for submission in prev_submissions:
        if submission.score >= score_obj.score:
            return error_response(request, HIGHER_SCORE_MESSAGE)

    # Check to ensure image / video is proper
    res = submission_screenshot_check(score_obj, request)
    if (res is not None):
        return res

    # Check the clean code
    res = freight_frenzy_clean_code_check(score_obj, request)
    if (res is not None):
        return res

    # Code is valid! Instantly approve!
    approve_score(score_obj, prev_submissions)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


@login_required(login_url='/login')
def tipping_point_submit(request):
    if request.method != 'POST':
        return render(request, SUBMIT_PAGE, {"form": TPScoreForm})

    form = TPScoreForm(request.POST)
    if not form.is_valid():
        return render(request, SUBMIT_PAGE, {"form": form})

    # Set up the score object
    score_obj = extract_form_data(form, request)

    # Check for older submissions from this user in this category
    prev_submissions = Score.objects.filter(
        leaderboard__name=score_obj.leaderboard, player=score_obj.player)

    for submission in prev_submissions:
        if submission.score >= score_obj.score:
            return error_response(request, HIGHER_SCORE_MESSAGE)

    # Check to ensure image / video is proper
    res = submission_screenshot_check(score_obj, request)
    if (res is not None):
        return res

    # Check the clean code
    res = tipping_point_clean_code_check(score_obj, request)
    if (res is not None):
        return res

    # Code is valid! Instantly approve!
    approve_score(score_obj, prev_submissions)

    return render(request, SUBMIT_ACCEPTED_PAGE, {})


def extract_form_data(form: ScoreForm, request):
    score_obj = Score()
    score_obj.leaderboard = form.cleaned_data['leaderboard']
    score_obj.player = request.user
    score_obj.score = form.cleaned_data['score']
    score_obj.time_set = datetime.now()
    score_obj.approved = False
    score_obj.source = form.cleaned_data['source']
    score_obj.clean_code = form.cleaned_data['clean_code']

    return score_obj


def approve_score(score_obj: Score, prev_submissions):
    # Delete previous submissions for this category
    prev_submissions.delete()

    # Save the new submission
    score_obj.approved = True
    score_obj.save()

    code_obj = CleanCodeSubmission()
    code_obj.clean_code = score_obj.clean_code
    code_obj.player = score_obj.player
    code_obj.save()


def submission_screenshot_check(score_obj: Score, request):
    """ Checks if the submission has a screenshot and if it is valid.
    :param score_obj: Score object to check
    :return: None if valid, HTTPResponse with error message if not
    """
    try:
        if "youtube" in score_obj.source or "youtu.be" in score_obj.source:
            # YouTube video...
            # Extract the video id
            score_obj.source = score_obj.source[score_obj.source.rfind('/')+1:]
            if (score_obj.source.rfind('v=') != -1):
                score_obj.source = score_obj.source[score_obj.source.rfind(
                    'v=')+2:]
            if (score_obj.source.rfind('?') != -1):
                score_obj.source = score_obj.source[:score_obj.source.rfind(
                    '?')]
            if (score_obj.source.rfind('&') != -1):
                score_obj.source = score_obj.source[:score_obj.source.rfind(
                    '&')]
            # Check if the video exists
            urlopen(
                "http://img.youtube.com/vi/{}/mqdefault.jpg".format(score_obj.source))
            # Convert to embed
            score_obj.source = "https://www.youtube-nocookie.com/embed/" + score_obj.source
        elif "streamable" in score_obj.source:
            # Streamable video...
            # Check if the video exists
            urlopen("https://api.streamable.com/oembed.json?url=" +
                    score_obj.source)
            # Convert to embed
            score_obj.source = score_obj.source.replace(
                "streamable.com/", "streamable.com/e/")
        else:
            # Image...
            # Check to ensure proper file
            req = Request(score_obj.source, headers={
                          'User-Agent': USER_AGENT})
            res = urlopen(req).info()
            # check if the content-type is a image
            if res["content-type"] not in ("image/png", "image/jpeg", "image/jpg"):
                return error_response(request, BAD_URL_MESSAGE)
    except Exception:  # malformed url provided
        return error_response(request, BAD_URL_MESSAGE)

    return None  # no error, proper url provided


def infinite_recharge_clean_code_check(score_obj: Score, request):
    """ Checks if the clean code is valid.
    :param score_obj: Score object to check
    :param prev_submissions: List of previous submissions from this user in this category
    :return: None if valid, HTTPResponse with error message if not
    """
    try:
        # Clean code decryption
        clean_code_decryption(score_obj)

        # Clean code extraction
        restart_option, game_options, robot_model, blue_score, red_score, game_index = extract_clean_code_info(
            score_obj)

        # Check game settings
        res = check_generic_game_settings(score_obj, request)
        if (res is not None):
            return res
        res = check_infinite_recharge_game_settings(
            game_options, restart_option, game_index, request)
        if (res is not None):
            return res

        # Check robot type
        res = check_infinite_recharge_robot_type(
            score_obj, robot_model, request)
        if (res is not None):
            return res

        # Check score
        res = check_score(score_obj, blue_score, red_score, request)
        if (res is not None):
            return res

        # Search for code in database to ensure it is unique
        res = search_for_reused_code(score_obj, request)
        if (res is not None):
            return res

    except IndexError:  # code is for wrong game
        return error_response(request, ERROR_WRONG_GAME_MESSAGE)
    except Exception:  # code is corrupted during decryption
        return error_response(request, ERROR_CORRUPT_CODE_MESSAGE)

    return None  # no error, proper clean code provided


def rapid_react_clean_code_check(score_obj: Score, request):
    """ Checks if the clean code is valid.
    :param score_obj: Score object to check
    :param prev_submissions: List of previous submissions from this user in this category
    :return: None if valid, HTTPResponse with error message if not
    """
    try:
        # Clean code decryption
        clean_code_decryption(score_obj)

        # Clean code extraction
        restart_option, game_options, robot_model, blue_score, red_score, game_index = extract_clean_code_info(
            score_obj)

        # Check game settings
        res = check_generic_game_settings(score_obj, request)
        if (res is not None):
            return res
        res = check_rapid_react_game_settings(
            game_options, restart_option, game_index, request)
        if (res is not None):
            return res

        # Check robot type
        res = check_rapid_react_robot_type(score_obj, robot_model, request)
        if (res is not None):
            return res

        # Check score
        res = check_rapid_react_score(
            score_obj, blue_score, red_score, request)
        if (res is not None):
            return res

        # Search for code in database to ensure it is unique
        res = search_for_reused_code(score_obj, request)
        if (res is not None):
            return res

    except IndexError:  # code is for wrong game
        return error_response(request, ERROR_WRONG_GAME_MESSAGE)
    except Exception:  # code is corrupted during decryption
        return error_response(request, ERROR_CORRUPT_CODE_MESSAGE)

    return None  # no error, proper clean code provided


def freight_frenzy_clean_code_check(score_obj: Score, request):
    """ Checks if the clean code is valid.
    :param score_obj: Score object to check
    :param prev_submissions: List of previous submissions from this user in this category
    :return: None if valid, HTTPResponse with error message if not
    """
    try:
        # Clean code decryption
        clean_code_decryption(score_obj)

        # Clean code extraction
        restart_option, game_options, robot_model, blue_score, red_score, game_index = extract_clean_code_info(
            score_obj)

        # Check game settings
        res = check_generic_game_settings(score_obj, request)
        if (res is not None):
            return res
        res = check_freight_frenzy_game_settings(
            game_options, game_index, request)
        if (res is not None):
            return res

        # Check robot type
        res = check_freight_frenzy_robot_type(score_obj, robot_model, request)
        if (res is not None):
            return res

        # Check score
        res = check_score(score_obj, blue_score, red_score, request)
        if (res is not None):
            return res

        # Search for code in database to ensure it is unique
        res = search_for_reused_code(score_obj, request)
        if (res is not None):
            return res

    except IndexError:  # code is for wrong game
        return error_response(request, ERROR_WRONG_GAME_MESSAGE)
    except Exception:  # code is corrupted during decryption
        return error_response(request, ERROR_CORRUPT_CODE_MESSAGE)

    return None  # no error, proper clean code provided


def tipping_point_clean_code_check(score_obj: Score, request):
    """ Checks if the clean code is valid.
    :param score_obj: Score object to check
    :param prev_submissions: List of previous submissions from this user in this category
    :return: None if valid, HTTPResponse with error message if not
    """
    try:
        # Clean code decryption
        clean_code_decryption(score_obj)

        # Clean code extraction
        restart_option, game_options, robot_model, blue_score, red_score, game_index = extract_clean_code_info(
            score_obj)

        # Check game settings
        res = check_generic_game_settings(score_obj, request)
        if (res is not None):
            return res
        res = check_tipping_point_game_settings(game_index, request)
        if (res is not None):
            return res

        # Check robot type
        res = check_tipping_point_robot_type(score_obj, robot_model, request)
        if (res is not None):
            return res

        # Check score
        res = check_score(score_obj, blue_score, red_score, request)
        if (res is not None):
            return res

        # Search for code in database to ensure it is unique
        res = search_for_reused_code(score_obj, request)
        if (res is not None):
            return res

    except IndexError:  # code is for wrong game
        return error_response(request, ERROR_WRONG_GAME_MESSAGE)
    except Exception:  # code is corrupted during decryption
        return error_response(request, ERROR_CORRUPT_CODE_MESSAGE)

    return None  # no error, proper clean code provided


def extract_clean_code_info(score_obj: Score):
    dataset = score_obj.decrypted_code.split(',')

    score_obj.client_version = dataset[0].strip()
    game_index = dataset[1].strip()
    score_obj.time_of_score = dataset[2].strip()
    red_score = dataset[3].strip()
    blue_score = dataset[4].strip()
    score_obj.robot_position = dataset[5].strip()
    robot_model = dataset[6].strip()
    restart_option = dataset[7].strip()
    game_options = dataset[8].strip().split(':')
    return restart_option, game_options, robot_model, blue_score, red_score, game_index


def clean_code_decryption(score_obj):
    indata = score_obj.clean_code.replace(' ', '')
    ivseed = indata[-4:] * 4
    data = bytes.fromhex(indata[:-4])

    # Decrypt
    cipher = AES.new(NEW_AES_KEY.encode("utf-8"),
                     AES.MODE_CBC, ivseed.encode("utf-8"))
    score_obj.decrypted_code = cipher.decrypt(data).decode("utf-8")


def check_generic_game_settings(score_obj: Score, request):
    """ Checks if the universal game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if float(score_obj.client_version[1:4]) < 7.1 or score_obj.client_version == 'v7.1a' or \
            score_obj.client_version == 'v7.1b' or score_obj.client_version == 'v7.1c':
        return error_response(request, WRONG_VERSION_MESSAGE)
    if "pre" in score_obj.client_version:
        return error_response(request, PRERELEASE_MESSAGE)

    return None  # No error


def check_infinite_recharge_game_settings(game_options: list, restart_option: str, game_index: str, request):
    """ Checks if the Infinite Recharge game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '4'):
        return error_response(request, 'Wrong game! This form is for Infinite Recharge.')
    if (restart_option != '2'):
        return error_response(request, 'You must use restart option 2 for high score submissions.')
    if (game_options[25] != '2021'):
        return error_response(request, 'You must use Game Version 2021 for high score submissions.')
    if (game_options[7] != '0'):
        return error_response(request, 'You may not use power-ups for high score submissions.')
    if (game_options[26][0] != '0'):
        return error_response(request, 'You must use shield power-cell offset of 0 for high score submissions.')
    if (game_options[24] != '0'):
        return error_response(request, 'Overflow balls must be set to spawn in center for high score submissions.')

    return None  # No error


def check_rapid_react_game_settings(game_options: list, restart_option: str, game_index: str, request):
    """ Checks if the Rapid React game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '10'):
        return error_response(request, 'Wrong game! This form is for Rapid React.')
    if (game_options[0] != '1'):
        return error_response(request, 'You must have autonomous wall setting enabled for high score submissions.')
    if (game_options[3] != '1'):
        return error_response(request, 'You must enable possession limit for high score submissions.')
    if (game_options[4] != '4'):
        return error_response(request, 'You must set possession limit penalty to 4 points for high score submissions.')
    if (game_options[5] != '0'):
        return error_response(request, 'You may not use power-ups for high score submissions.')

    return None  # No error


def check_freight_frenzy_game_settings(game_options: list, game_index: str, request):
    """ Checks if the Freight Frenzy game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """

    if (game_index != '9'):
        return error_response(request, 'Wrong game! This form is for Freight Frenzy.')
    if (game_options[3] != '1'):
        return error_response(request, 'You must enable possession limit for high score submissions.')

    return None  # No error


def check_tipping_point_game_settings(game_index: str, request):
    """ Checks if the Tipping Point game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """

    if (game_index != '8'):
        return error_response(request, 'Wrong game! This form is for Tipping Point.')

    return None  # No error


def check_infinite_recharge_robot_type(score_obj: Score, robot_model: str, request):
    """ Checks if the robot type is valid for Infinite Recharge.
    :return: None if the robot type is valid, or a response with an error message if it is not.
    """
    switch = {
        'OG': 'FRC shooter',
        'Inertia': 'NUTRONs 125',
        'Roboteers': 'Roboteers 2481',
        'Pushbot2': 'PushBot2',
        'Triangle': 'T Shooter',
        'Waffles': 'Waffles',
    }

    if switch[str(score_obj.leaderboard)] != robot_model:
        return error_response(request, WRONG_ROBOT_MESSAGE)

    return None  # No error


def check_rapid_react_robot_type(score_obj: Score, robot_model: str, request):
    """ Checks if the robot type is valid for Rapid React.
    :return: None if the robot type is valid, or a response with an error message if it is not.
    """
    switch = {
        'MiniDrone': 'RR_MiniDrone',
        'RRBulldogs': 'RR_Bulldogs',
        'RRFRCShooter': 'RR_FRC_Shooter',
    }

    if switch[str(score_obj.leaderboard)] != robot_model:
        return error_response(request, WRONG_ROBOT_MESSAGE)

    return None  # No error


def check_freight_frenzy_robot_type(score_obj: Score, robot_model: str, request):
    """ Checks if the robot type is valid for Freight Frenzy.
    :return: None if the robot type is valid, or a response with an error message if it is not.
    """
    switch = {
        'Bulldogs': 'Bulldogs',
        'Kraken': 'KrakenPinion',
        'Bailey': 'Bailey',
        'Cody': 'Cody',
        'goBILDA': 'goBILDA_ff',
        'DualMeta': 'dual_meta',
    }

    if switch[str(score_obj.leaderboard)] != robot_model:
        return error_response(request, WRONG_ROBOT_MESSAGE)

    return None  # No error


def check_tipping_point_robot_type(score_obj: Score, robot_model: str, request):
    """ Checks if the robot type is valid for Tipping Point.
    :return: None if the robot type is valid, or a response with an error message if it is not.
    """
    switch = {
        'AMOGO2': 'AMOGO_v2',
    }

    if switch[str(score_obj.leaderboard)] != robot_model:
        return error_response(request, WRONG_ROBOT_MESSAGE)

    return None  # No error


def check_score(score_obj: Score, blue_score: str, red_score: str, request):
    """ Checks if the true score matches the reported score.
    :return: None if the score is valid, or a response with an error message if it is not.
    """
    if score_obj.robot_position.startswith('Blue'):
        if (blue_score != str(score_obj.score)):
            return error_response(request, 'Double-check the score that you entered!')
    else:
        if (red_score != str(score_obj.score)):
            return error_response(request, 'Double-check the score that you entered!')

    return None  # No error


def check_rapid_react_score(score_obj: Score, blue_score: str, red_score: str, request):
    """ Checks if the true score matches the reported score.
    In Rapid React single player, your calculated score is your score minus the opponent's score.
    :return: None if the score is valid, or a response with an error message if it is not.
    """
    if score_obj.robot_position.startswith('Blue'):
        score = int(blue_score) - int(red_score)
        if (score != score_obj.score):
            return error_response(request, 'Double-check the score that you entered! For Rapid React, your calculated score is your score minus the opponent\'s score.')
    else:
        score = int(red_score) - int(blue_score)
        if (score != score_obj.score):
            return error_response(request, 'Double-check the score that you entered! For Rapid React, your calculated score is your score minus the opponent\'s score.')

    return None  # No error


def search_for_reused_code(score_obj: Score, request):
    """ Checks if the code has been previously submitted.
    :return: None if the code has not been previously submitted, or a response with an error message if it has.
    """
    clean_code_search = CleanCodeSubmission.objects.filter(
        clean_code=score_obj.clean_code)

    if clean_code_search.exists():
        # Uh oh, this user submitted a clean code that has already been used.
        # Report this via email.

        message = f"{score_obj.player} attempted (and failed) to submit a score: [{score_obj.score}] - {score_obj.leaderboard}\n\n This score was already submitted by {clean_code_search[0].player}\n\n {score_obj.source}\n\nhttps://secondrobotics.org/admin/highscores/score/"
        try:
            if (not DEBUG):
                send_mail(f"Possible cheating attempt from {score_obj.player}", message, "noreply@secondrobotics.org", [
                          'brennan@secondrobotics.org'], fail_silently=False)
        except Exception as ex:
            print(ex)

        return error_response(request, 'That clean code has already been submitted by another player.')

    return None  # No error
