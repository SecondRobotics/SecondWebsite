from django.http import HttpRequest
from django.core.mail import send_mail

from .models import Score, CleanCodeSubmission, ExemptedIP
from .forms import ScoreForm
from SRCweb.settings import NEW_AES_KEY, DEBUG, ADMIN_EMAILS, EMAIL_HOST_USER

from typing import Callable, Union
from Crypto.Cipher import AES
from urllib.request import urlopen, Request

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'

WRONG_ROBOT_MESSAGE = 'Double-check the robot type that you selected!'
HIGHER_SCORE_MESSAGE = 'You already have a submission with an equal or higher score than this!'
ERROR_WRONG_GAME_MESSAGE = 'There is something wrong with your clean code! Are you submitting for the right game?'
ERROR_CORRUPT_CODE_MESSAGE = 'There is something wrong with your clean code! Make sure you copied it properly.'
BAD_URL_MESSAGE = 'There is something wrong with the URL you provided for your screenshot/video. Please ensure you provide a link to a PNG, JPEG, YouTube video, or Streamable video.'
WRONG_VERSION_MESSAGE = 'Your version of the game is outdated and not supported. Please update to the latest version at https://xrcsimulator.org/downloads/.'
PRERELEASE_MESSAGE = 'Pre-release versions are not allowed for high score submission!'
WRONG_AUTO_OR_TELEOP_MESSAGE = 'Incorrect choice for control mode! Ensure you are submitting to the correct leaderboard for autonomous or tele-operated play.'


def submit_score(score_obj: Score, clean_code_check_func: Callable[[Score], Union[str, None]]) -> Union[str, None]:
    # Check to ensure image / video is proper
    res = submission_screenshot_check(score_obj)
    if (res is not None):
        return res

    # Check the clean code
    res = clean_code_check_func(score_obj)
    if (res is not None):
        return res

    # Check for older submissions from this user in this category
    prev_submissions = Score.objects.filter(
        leaderboard__name=score_obj.leaderboard, player=score_obj.player)

    for submission in prev_submissions:
        if submission.score >= score_obj.score:
            return HIGHER_SCORE_MESSAGE

    # Code is valid! Instantly approve!
    approve_score(score_obj, prev_submissions)

    return None  # No error


def submit_infinite_recharge(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, infinite_recharge_clean_code_check)


def submit_rapid_react(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, rapid_react_clean_code_check)


def submit_charged_up(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, charged_up_clean_code_check)


def submit_freight_frenzy(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, freight_frenzy_clean_code_check)


def submit_power_play(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, power_play_clean_code_check)


def submit_tipping_point(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, tipping_point_clean_code_check)


def submit_spin_up(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, spin_up_clean_code_check)


def submit_centerstage(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, centerstage_clean_code_check)


def submit_over_under(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, over_under_clean_code_check)


def submit_crescendo(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, crescendo_clean_code_check)


def submit_high_stakes(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, high_stakes_clean_code_check)


def submit_ultimate_goal(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, ultimate_goal_clean_code_check)


def submit_into_the_deep(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, into_the_deep_clean_code_check)


def submit_rover_ruckus(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, rover_ruckus_clean_code_check)


def submit_skystone(score_obj: Score) -> Union[str, None]:
    return submit_score(score_obj, skystone_clean_code_check)


def decode_time_data(in_string: str) -> str:
    out_bytes = ""

    for i in range(1, len(in_string), 2):
        out_bytes += in_string[i]

    j = len(in_string)-1
    if len(in_string) % 2 == 0:
        j -= 1

    while j >= 0:
        out_bytes += in_string[j]
        j -= 2

    return out_bytes


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip  # type: ignore


def extract_form_data(form: ScoreForm, request: HttpRequest) -> Score:
    score_obj = Score()
    score_obj.leaderboard = form.cleaned_data['leaderboard']
    score_obj.player = request.user  # type: ignore
    score_obj.score = form.cleaned_data['score']
    score_obj.approved = False
    score_obj.source = form.cleaned_data['source']
    score_obj.clean_code = form.cleaned_data['clean_code']
    score_obj.ip = get_client_ip(request)

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
    code_obj.score = score_obj.score
    code_obj.leaderboard = score_obj.leaderboard
    code_obj.ip = score_obj.ip
    code_obj.save()


def submission_screenshot_check(score_obj: Score) -> Union[str, None]:
    """ Checks if the submission has a screenshot and if it is valid.
    :param score_obj: Score object to check
    :return: None if valid, HttpResponse with error message if not
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
                return BAD_URL_MESSAGE
    except Exception:  # malformed url provided
        return BAD_URL_MESSAGE

    return None  # no error, proper url provided


def clean_code_check(score_obj: Score, settings_callback: Callable[[list[str], str, str], Union[str, None]], score_callback: Callable[[Score, str, str], Union[str, None]]) -> Union[str, None]:
    """ Checks if the clean code is valid.
    :param score_obj: Score object to check
    :return: None if valid, HttpResponse with error message if not
    """
    try:
        # Clean code decryption
        clean_code_decryption(score_obj)

        # Clean code extraction
        restart_option, game_options, robot_model, blue_score, red_score, game_index, auto_or_teleop, timer_left = extract_clean_code_info(
            score_obj)

        # Check game settings
        res = check_generic_game_settings(score_obj, auto_or_teleop)
        if (res is not None):
            return res
        res = settings_callback(game_options, restart_option, game_index)
        if (res is not None):
            return res

        # Check robot type
        res = check_robot_type(score_obj, robot_model)
        if (res is not None):
            return res

        # Check score
        res = score_callback(score_obj, blue_score, red_score)
        if (res is not None):
            return res

        # Check if time data has been tampered with
        search_for_violating_time_data(score_obj, timer_left, game_index)

        # Search for code in database to ensure it is unique
        res = search_for_reused_code(score_obj)
        if (res is not None):
            return res

    except IndexError:  # code is for wrong game
        return ERROR_WRONG_GAME_MESSAGE
    except Exception as e:  # code is corrupted during decryption
        return ERROR_CORRUPT_CODE_MESSAGE

    return None  # no error, proper clean code provided


def infinite_recharge_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_infinite_recharge_game_settings, check_score)


def rapid_react_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_rapid_react_game_settings, check_subtraction_score)


def charged_up_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_charged_up_game_settings, check_score)


def freight_frenzy_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_freight_frenzy_game_settings, check_score)


def power_play_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_power_play_game_settings, check_skills_challenge_score)


def tipping_point_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_tipping_point_game_settings, check_skills_challenge_score)


def spin_up_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_spin_up_game_settings, check_skills_challenge_score)


def centerstage_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_centerstage_game_settings, check_score)


def over_under_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_over_under_game_settings, check_score)


def crescendo_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_crescendo_game_settings, check_subtraction_score)


def high_stakes_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_high_stakes_game_settings, check_skills_challenge_score)


def ultimate_goal_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_ultimate_goal_game_settings, check_score)


def into_the_deep_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_into_the_deep_game_settings, check_subtraction_score)


def rover_ruckus_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_rover_ruckus_game_settings, check_subtraction_score)


def skystone_clean_code_check(score_obj: Score) -> Union[str, None]:
    return clean_code_check(score_obj, check_skystone_game_settings, check_subtraction_score)


def extract_clean_code_info(score_obj: Score) -> tuple[str, list[str], str, str, str, str, str, str]:
    """ Extracts the relevant information from the clean code.
    :param score_obj: Score object to extract from
    :return: Tuple of the relevant information
    """
    if not score_obj.decrypted_code:
        raise Exception("Code not decrypted")

    dataset = score_obj.decrypted_code.split(',')

    score_obj.client_version = dataset[0].strip()
    game_index = dataset[1].strip()
    score_obj.time_of_score = dataset[2].strip()
    red_score = dataset[3].strip()
    blue_score = dataset[4].strip()
    score_obj.robot_position = dataset[5].strip()
    robot_model = dataset[6].strip()
    auto_or_teleop = dataset[7].strip()
    restart_option = dataset[8].strip()
    game_options = dataset[9].strip().split(':')
    timer_left = dataset[10].strip()

    time_data = ""
    for i in range(11, len(dataset)):
        time_data += decode_time_data(dataset[i].strip()) + "\n"
    score_obj.time_data = time_data[:-1]

    return restart_option, game_options, robot_model, blue_score, red_score, game_index, auto_or_teleop, timer_left


def clean_code_decryption(score_obj: Score) -> None:
    """ Decrypts the clean code.
    :param score_obj: Score object to decrypt
    Decrypted code is stored in score_obj.decrypted_code
    """
    indata = score_obj.clean_code.replace(' ', '')
    ivseed = indata[-4:] * 4
    data = bytes.fromhex(indata[:-4])

    # Decrypt
    cipher = AES.new(NEW_AES_KEY.encode("utf-8"),
                     AES.MODE_CBC, ivseed.encode("utf-8"))
    score_obj.decrypted_code = cipher.decrypt(data).decode("utf-8")


def check_generic_game_settings(score_obj: Score, auto_or_teleop: str) -> Union[str, None]:
    """ Checks if the universal game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (not score_obj.client_version or float(score_obj.client_version[1:5]) < 13.1
            or score_obj.client_version == 'v13.1a'):
        return WRONG_VERSION_MESSAGE
    if "_p" in score_obj.client_version:
        return PRERELEASE_MESSAGE
    if score_obj.leaderboard.auto_or_teleop != auto_or_teleop:
        return WRONG_AUTO_OR_TELEOP_MESSAGE

    return None  # No error


def check_infinite_recharge_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Infinite Recharge game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '4'):
        return 'Wrong game! This form is for Infinite Recharge.'
    if (restart_option != '2'):
        return 'You must use restart option 2 for high score submissions.'
    if (game_options[25] != '2021'):
        return 'You must use Game Version 2021 for high score submissions.'
    if (game_options[7] != '0'):
        return 'You may not use power-ups for high score submissions.'
    if (game_options[26][0] != '0'):
        return 'You must use shield power-cell offset of 0 for high score submissions.'
    if (game_options[24] != '0'):
        return 'Overflow balls must be set to spawn in center for high score submissions.'

    return None  # No error


def check_rapid_react_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Rapid React game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '10'):
        return 'Wrong game! This form is for Rapid React.'
    if (game_options[0] != '1'):
        return 'You must have autonomous wall setting enabled for high score submissions.'
    if (game_options[3] != '1'):
        return 'You must enable possession limit for high score submissions.'
    if (game_options[4] != '4'):
        return 'You must set possession limit penalty to 4 points for high score submissions.'
    if (game_options[5] != '0'):
        return 'You may not use power-ups for high score submissions.'

    return None  # No error


def check_charged_up_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Charged Up game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '13'):
        return 'Wrong game! This form is for Charged Up.'
    if (game_options[7] != '0'):
        return 'You may not use power-ups for high score submissions.'

    return None  # No error


def check_freight_frenzy_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Freight Frenzy game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '9'):
        return 'Wrong game! This form is for Freight Frenzy.'
    if (game_options[3] != '1'):
        return 'You must enable possession limit for high score submissions.'

    return None  # No error


def check_power_play_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Power Play game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '12'):
        return 'Wrong game! This form is for Power Play.'

    return None  # No error


def check_tipping_point_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Tipping Point game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '8'):
        return 'Wrong game! This form is for Tipping Point.'
    if (restart_option != '2'):
        return 'You must use restart option 2 (skills challenge) for Tipping Point high score submissions.'

    return None  # No error


def check_spin_up_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Spin Up game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '11'):
        return 'Wrong game! This form is for Spin Up.'
    if (restart_option != '2'):
        return 'You must use restart option 2 (skills challenge) for Spin Up high score submissions.'

    return None  # No error


def check_centerstage_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Center Stage game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '15'):
        return 'Wrong game! This form is for Centerstage.'

    return None  # No error


def check_over_under_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Over Under game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '14'):
        return 'Wrong game! This form is for Over Under.'
    if (restart_option != '2'):
        return 'You must use restart option 2 (skills challenge) for Over Under high score submissions.'

    return None  # No error


def check_crescendo_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Crescendo game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '16'):
        return 'Wrong game! This form is for Crescendo.'
    if (game_options[2] != '1'):
        return 'You must have possession limit enabled for high score submissions.'
    if (game_options[6] != '0'):
        return 'You may not use power-ups for high score submissions.'

    return None  # No error


def check_high_stakes_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the High Stakes game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '17'):
        return 'Wrong game! This form is for High Stakes.'
    if (restart_option != '2'):
        return 'You must use restart option 2 (skills challenge) for High Stakes high score submissions.'
    if (game_options[0] != '1'):
        return 'You must have auto wall enabled for high score submissions.'

    return None  # No error


def check_ultimate_goal_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the High Stakes game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '7'):
        return 'Wrong game! This form is for Ultimate Goal.'
    if (game_options[0] != '30'):
        return 'Major Penalties must be worth 30 points.'

    return None  # No error


def check_into_the_deep_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Into The Deep game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '18'):
        return 'Wrong game! This form is for Into The Deep.'

    return None  # No error


def check_rover_ruckus_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Rover Ruckus game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '2'):
        return 'Wrong game! This form is for Rover Ruckus.'

    return None  # No error


def check_skystone_game_settings(game_options: list, restart_option: str, game_index: str) -> Union[str, None]:
    """ Checks if the Skystone game settings are valid.
    :return: None if the settings are valid, or a response with an error message if they are not.
    """
    if (game_index != '3'):
        return 'Wrong game! This form is for Skystone.'
    if (game_options[0] != '1'):
        return 'You must have depot pushback enabled for high score submissions.'
    if (game_options[1] != '1' or game_options[5] != '5'):
        return 'You must have crossing under enemy skybridge penalty enabled and set to 5 pts for high score submissions.'
    if (game_options[4] != '1' or game_options[8] != '5'):
        return 'You must have possession limit penalty enabled and set to 5 pts for high score submissions.'
    if (game_options[9] != '500'):
        return 'Possession grace period must be set to 500 ms for high score submissions.'

    return None  # No error


def check_robot_type(score_obj: Score, robot_model: str) -> Union[str, None]:
    """ Checks if the robot model is valid.
    :return: None if the robot model is valid, or a response with an error message if it is not.
    """
    if score_obj.leaderboard.robot != robot_model:
        return WRONG_ROBOT_MESSAGE

    return None  # No error


def check_score(score_obj: Score, blue_score: str, red_score: str) -> Union[str, None]:
    """ Checks if the true score matches the reported score.
    :return: None if the score is valid, or a response with an error message if it is not.
    """
    if not score_obj.robot_position:
        return 'You must specify a robot position.'

    if score_obj.robot_position.startswith('Blue'):
        score_obj.score = int(blue_score)
        # if (blue_score != str(score_obj.score)):
        #     return 'Double-check the score that you entered!'
    else:
        score_obj.score = int(red_score)
        # if (red_score != str(score_obj.score)):
        #     return 'Double-check the score that you entered!'

    return None  # No error


def check_skills_challenge_score(score_obj: Score, blue_score: str, red_score: str) -> Union[str, None]:
    """ Checks if the true score matches the reported score.
    In Skills Challenge, your score is the sum of both alliances' scores.
    :return: None if the score is valid, or a response with an error message if it is not.
    """
    score = int(blue_score) + int(red_score)
    score_obj.score = score
    # if (score != score_obj.score):
    #     return 'Double-check the score that you entered! For Skills Challenge, your score is the sum of both alliances\' scores.'

    return None  # No error


def check_subtraction_score(score_obj: Score, blue_score: str, red_score: str) -> Union[str, None]:
    """ Checks if the true score matches the reported score.
    Your calculated score is your score minus the opponent's score.
    :return: None if the score is valid, or a response with an error message if it is not.
    """
    if not score_obj.robot_position:
        return 'You must specify a robot position.'

    if score_obj.robot_position.startswith('Blue'):
        score = int(blue_score) - int(red_score)
        score_obj.score = score
        # if (score != score_obj.score):
        #     return 'Double-check the score that you entered! For Rapid React, your calculated score is your score minus the opponent\'s score.'
    else:
        score = int(red_score) - int(blue_score)
        score_obj.score = score
        # if (score != score_obj.score):
        #     return 'Double-check the score that you entered! For Rapid React, your calculated score is your score minus the opponent\'s score.'

    return None  # No error


def search_for_reused_code(score_obj: Score) -> Union[str, None]:
    """ Checks if the code has been previously submitted.
    :return: None if the code has not been previously submitted, or a response with an error message if it has.
    """
    clean_code_search = CleanCodeSubmission.objects.filter(
        clean_code=score_obj.clean_code)

    if clean_code_search.exists():
        if clean_code_search[0].player == score_obj.player:
            # This is the same player, so it's okay.
            return 'That clean code has already been submitted by you (maybe you submitted it twice?).'

        # Uh oh, this user submitted a clean code that has already been used.
        # Report this via email.

        message = f"{score_obj.player} ({score_obj.ip}) attempted (and failed) to submit a score: [{score_obj.score}] - {score_obj.leaderboard}\n\n This score was already submitted by {clean_code_search[0].player} ({clean_code_search[0].ip})\n\n {score_obj.source}\n\nhttps://secondrobotics.org/admin/highscores/score/"
        try:
            if (not DEBUG):
                send_mail(f"Duplicate clean code usage from {score_obj.player}",
                          message, EMAIL_HOST_USER, ADMIN_EMAILS, fail_silently=False)
        except Exception as ex:
            print(ex)

        return 'That clean code has already been submitted by another player.'

    # same ip but different player
    ip_search = CleanCodeSubmission.objects.filter(
        ip=score_obj.ip).exclude(player=score_obj.player)

    if ip_search.exists():
        # search if an exemption exists
        exempted_ip_search = ExemptedIP.objects.filter(ip=score_obj.ip)
        if exempted_ip_search.exists():
            return None

        # Uh oh, there are multiple users submitting from the same IP.
        # Report this via email.

        message = f"{score_obj.player} ({score_obj.ip}) submitted a score (successfully): [{score_obj.score}] - {score_obj.leaderboard}\n\n This IP has also been used by {ip_search[0].player} ({ip_search[0].ip})\n\n {score_obj.source}\n\nhttps://secondrobotics.org/admin/highscores/score/"
        try:
            if (not DEBUG):
                send_mail(f"Duplicate IP usage from {score_obj.player}",
                          message, EMAIL_HOST_USER, ADMIN_EMAILS, fail_silently=False)
        except Exception as ex:
            print(ex)

        # Still allow the score to be submitted.

    return None  # No error


def search_for_violating_time_data(score_obj: Score, timer_left: str, game_index: str) -> None:
    res = check_time_data(score_obj, timer_left, game_index)
    if res:
        # Uh oh, there are possible indicators of cheating in the time data.
        # Report this via email.

        print(res)
        message = f"{score_obj.player} ({score_obj.ip}) submitted a score (successfully) with concerning time data: [{score_obj.score}] - {score_obj.leaderboard}\n{res}\n{score_obj.time_data}\n\nhttps://secondrobotics.org/admin/highscores/score/"
        try:
            if (not DEBUG):
                send_mail(f"Concerning time data from {score_obj.player}",
                          message, EMAIL_HOST_USER, ADMIN_EMAILS, fail_silently=False)
        except Exception as ex:
            print(ex)


def check_time_data(score_obj: Score, timer_left: str, game_index: str) -> Union[str, None]:
    """ Checks the time data for indicators of cheating.
    :return: None if the time data is valid, or a response with an error message if it is not.
    """
    if not score_obj.time_data:
        return 'No time data was submitted.'

    # timer_left is in x:xx.x format
    seconds_left = int(timer_left.split(
        ':')[0]) * 60 + float(timer_left.split(':')[1])
    game_time_elapsed = get_game_length(game_index) - seconds_left
    min_time_data = min(int(game_time_elapsed/10), 1)

    time_data = score_obj.time_data.split('\n')

    last_time = 0
    for i in range(len(time_data)):
        step = time_data[i].split('|')

        if len(step) < 7:
            return f'Invalid length of time data array at step {i+1} (should be 7).'
        if float(step[0]) - last_time > 12:
            return f'Too long of a gap between steps {i} and {i+1} (should be ~10 seconds apart).'
        if float(step[0]) - last_time < 8 and last_time != 0:
            return f'Too short of a gap between steps {i} and {i+1} (should be ~10 seconds apart).'

        last_time = float(step[0])

    if len(time_data) < min_time_data:
        return f'Not enough time data was submitted (should be at least {min_time_data} steps for {game_time_elapsed}s game).'

    return None  # No error


def get_game_length(game_index: str):
    """ Returns the length of the game in seconds."""
    # VEX games (skills challenges) are 60 seconds long
    if game_index in ["8", "14", "17"]:
        return 60
    # All other games are 2:30 (150 seconds) long
    return 150


game_slug_to_submit_func = {
    "ir": submit_infinite_recharge,
    "rr": submit_rapid_react,
    "cu": submit_charged_up,
    "ff": submit_freight_frenzy,
    "pp": submit_power_play,
    "tp": submit_tipping_point,
    "su": submit_spin_up,
    "cs": submit_centerstage,
    "ou": submit_over_under,
    "cr": submit_crescendo,
    "hs": submit_high_stakes,
    "ug": submit_ultimate_goal,
    "id": submit_into_the_deep,
    "ro": submit_rover_ruckus,
    "ss": submit_skystone,
}

game_to_submit_func = {
    "Infinite Recharge": submit_infinite_recharge,
    "Rapid React": submit_rapid_react,
    "Charged Up": submit_charged_up,
    "Freight Frenzy": submit_freight_frenzy,
    "Power Play": submit_power_play,
    "Tipping Point": submit_tipping_point,
    "Spin Up": submit_spin_up,
    "CENTERSTAGE": submit_centerstage,
    "Over Under": submit_over_under,
    "Crescendo": submit_crescendo,
    "High Stakes": submit_high_stakes,
    "Ultimate Goal": submit_ultimate_goal,
    "INTO THE DEEP": submit_into_the_deep,
    "Rover Ruckus": submit_rover_ruckus,
    "Skystone": submit_skystone,
}
