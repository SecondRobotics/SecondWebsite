from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.http import HttpResponse
from .models import Leaderboard, Score, CleanCodeSubmission
from datetime import datetime
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail, BadHeaderError
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max, Q

from django.conf import settings
from django.contrib import messages

from .forms import ScoreForm

from SRCweb.settings import CLEAN_AES_KEY, NEW_AES_KEY

from Crypto.Cipher import AES

# file._size > settings.MAX_UPLOAD_SIZE

# Create your views here.

def index(response, name):
    if not Leaderboard.objects.filter(name=name).exists():
        return HttpResponseRedirect(response.META.get('HTTP_REFERER', '/'))
    # ls = Leaderboard.objects.get(name=name)
    sorted = Score.objects.filter(leaderboard__name=name, approved=True).order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted:
        context.append([i, item])
        i+=1

    return render(response, "highscores/leaderboard_ranks.html", {"ls": context, "robot_name":name})

def combined(request):
    scores = Score.objects.filter(~Q(leaderboard__name="Pushbot2"), approved=True).values('player_name').annotate(time_set=Max('time_set')).annotate(score=Sum('score'))
    sorted = scores.order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted:
        context.append([i, item])
        i+=1

    return render(request, "highscores/combined_leaderboard.html", {"ls": context})


@login_required(login_url='/login')
def submit(request):
    if request.method == "POST":
        # uploaded_file = request.FILES.get('score-screenshot', False)
        
        form = ScoreForm(request.POST)
        if form.is_valid():
            # fs = FileSystemStorage()
            # fs.save(uploaded_file.name, uploaded_file)
            obj = Score()
            obj.leaderboard = form.cleaned_data['leaderboard']
            obj.player_name = request.user
            obj.score = form.cleaned_data['score']
            obj.time_set = datetime.now()
            obj.approved = False
            obj.source = form.cleaned_data['source']
            obj.clean_code = form.cleaned_data['clean_code']

            # Check for older submissions from this user in this category
            prev_submissions = Score.objects.filter(leaderboard__name=obj.leaderboard, player_name=obj.player_name)

            for submission in prev_submissions:
                if submission.score >= obj.score:
                    return HttpResponse('You already have a submission with an equal or higher score than this!')

            # If a clean code was entered...
            if obj.clean_code is not None:
                try:
                    # Clean code decryption
                    indata = obj.clean_code.replace(' ', '')
                    ivseed = indata[-4:] * 4
                    data = bytes.fromhex(indata[:-4])

                    try:
                        # v5.8c
                        cipher = AES.new(CLEAN_AES_KEY.encode("utf-8"), AES.MODE_CBC, ivseed.encode("utf-8"))
                        obj.decrypted_code = cipher.decrypt(data).decode("utf-8")
                    except Exception:
                        # v5.8d+
                        cipher = AES.new(NEW_AES_KEY.encode("utf-8"), AES.MODE_CBC, ivseed.encode("utf-8"))
                        obj.decrypted_code = cipher.decrypt(data).decode("utf-8")

                    # Clean code verification
                    dataset = obj.decrypted_code.split(',')

                    obj.client_version = dataset[0].strip()
                    obj.time_of_score = dataset[1].strip()
                    red_score = dataset[2].strip()
                    blue_score = dataset[3].strip()
                    obj.robot_position = dataset[4].strip()
                    robot_model = dataset[5].strip()
                    restart_option = dataset[6].strip()
                    game_options = dataset[7].strip().split(':')

                    # Check game settings
                    if float(obj.client_version[1:4]) < 5.8:
                        return HttpResponse('Game version too old! Update to v5.8+')
                    if (restart_option != '2'):
                        return HttpResponse('You must use restart option 2 for high score submissions.')
                    if (game_options[25] != '2021'):
                        return HttpResponse('You must use Game Version 2021 for high score submissions.')
                    if (game_options[7] != '0'):
                        return HttpResponse('You may not use power-ups for high score submissions.')
                    if (game_options[26][0] != '0'):
                        return HttpResponse('You must use shield power-cell offset of 0 for high score submissions.')
                    if (game_options[24] != '0'):
                        return HttpResponse('Overflow balls must be set to spawn in center for high score submissions.')

                    # Check robot type
                    if (str(obj.leaderboard) == 'OG'):
                        if (robot_model != 'FRC shooter'):
                            return HttpResponse('Double-check the robot type that you selected!')
                    elif (str(obj.leaderboard) == 'Inertia'):
                        if (robot_model != 'NUTRONs 125'):
                            return HttpResponse('Double-check the robot type that you selected!')
                    elif (str(obj.leaderboard) == 'Roboteers'):
                        if (robot_model != 'Roboteers 2481'):
                            return HttpResponse('Double-check the robot type that you selected!')
                    elif (str(obj.leaderboard) == 'Pushbot2'):
                        if (robot_model != 'PushBot2'):
                            return HttpResponse('Double-check the robot type that you selected!')
                    else:
                        return HttpResponse('Double-check the robot type that you selected!')

                    # Check score
                    if obj.robot_position.startswith('Blue'):
                        if (blue_score != str(obj.score)):
                            return HttpResponse('Double-check the score that you entered!')
                    else:
                        if (red_score != str(obj.score)):
                            return HttpResponse('Double-check the score that you entered!')

                    # Delete previous submissions for this category
                    prev_submissions.delete()

                    # Search for code in database
                    clean_code_search = CleanCodeSubmission.objects.filter(clean_code=obj.clean_code)

                    if clean_code_search.exists():
                        # Uh oh, this user submitted a clean code that has already been used.
                        # Report this via email.
                        
                        message = f"{obj.player_name} attempted (and failed) to submit a score: [{obj.score}] - {obj.leaderboard}\n\n This score was already submitted by {clean_code_search[0].player_name}\n\n {obj.source}\n\nhttps://secondrobotics.org/admin/highscores/score/"
                        try:
                            send_mail(f"Possible cheating attempt from {obj.player_name}", message, "noreply@secondrobotics.org", ['brennan@secondrobotics.org'], fail_silently=False)
                        except Exception as ex:
                            print(ex)

                        return HttpResponse('That clean code has already been submitted by another player.')

                    # Code is valid! Instantly approve!
                    obj.approved = True
                    obj.save()

                    code_obj = CleanCodeSubmission()
                    code_obj.clean_code = obj.clean_code
                    code_obj.player_name = obj.player_name
                    code_obj.save()

                    return render(request, "highscores/submit_accepted.html", {})

                except IndexError: # code is for wrong game
                    return HttpResponse('There is something wrong with your clean code! Are you submitting for the right game?')
                except Exception: # code is corrupted during decryption
                    return HttpResponse('There is something wrong with your clean code! Make sure you copied it properly.')

            obj.save()

            message = f"{obj.player_name} [{obj.score}] - {obj.leaderboard}\n\n {obj.source}\n\nhttps://secondrobotics.org/admin/highscores/score/"
            try:
                send_mail(f"New score from {obj.player_name}", message, "noreply@secondrobotics.org", ['brennan@secondrobotics.org'], fail_silently=False)
            except Exception as ex:
                print(ex)
            return render(request, "highscores/submit_success.html", {})
    else:
        form = ScoreForm
    return render(request, "highscores/submit.html", {"form": form})
