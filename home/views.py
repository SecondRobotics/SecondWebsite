from teamleague.models import Alliance
from django.http.response import HttpResponseRedirect
from discordoauth2.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

from highscores.models import CleanCodeSubmission, Score

def index(response):
    return render(response, "home/home.html", {})

def about(response):
    return render(response, "home/about.html", {})

def mrc(response):
    return render(response, "home/mrc.html", {})

def rules(response):
    return render(response, "home/rules.html", {})

def staff(response):
    return render(response, "home/staff.html", {})

def privacy(response):
    return render(response, "home/privacy.html", {})

def src_rules(response):
    return redirect('https://bit.ly/SRCrules')

def stc_rules(response):
    return redirect('https://bit.ly/STC-rules')

def mrc_rules(response):
    return redirect('https://bit.ly/MRC-rules')

def discord(response):
    return redirect('https://www.discord.gg/Zq3HXRc')

def ranked(response):
    return redirect('https://bit.ly/EloRanks')

def merch(response):
    return redirect('https://second-robotics.creator-spring.com/')

def hall_of_fame(response):
    return render(response, "home/hall_of_fame.html", {})

def logos(response):
    return render(response, "home/logos.html", {})

def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
        return redirect('/oauth2/login')

def logout_user(request):
    logout(request)
    return redirect('/')

def reauth_user(request):
    logout(request)
    return redirect('/oauth2/login')

def user_profile(request, user_id):
    user_search = User.objects.filter(id=user_id)
    if not user_search.exists():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    user = user_search[0]

    scoresdata = Score.objects.filter(~Q(leaderboard__name="Pushbot2"), player=user, approved=True)
    scores = {"overall": 0}
    sources = {}
    for score in scoresdata:
        sources.update({score.leaderboard.name: score.source})
        scores.update({score.leaderboard.name: score.score})
        scores.update({"overall": score.score + scores['overall']})
    context={"scores": scores, "user": user, "sources": sources}
    return render(request, "home/user_profile.html", context)

@login_required(login_url='/login')
def merge_legacy_account(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = User.objects.filter(username=username)
        if user.exists():
            user = user[0]

            if password and len(password) > 3 and user.check_password(password) and user.is_active:
                # Copy attributes from old user to new user
                for score in Score.objects.filter(player=user):
                    score.player = request.user
                    score.save()
                for score in CleanCodeSubmission.objects.filter(player=user):
                    score.player = request.user
                    score.save()
                for team in Alliance.objects.all():
                    if team.player1_user == user:
                        team.player1_user = request.user
                        team.save()
                        break
                    if team.player2_user == user:
                        team.player2_user = request.user
                        team.save()
                        break
                    if team.player3_user == user:
                        team.player3_user = request.user
                        team.save()
                        break

                request.user.date_joined = user.date_joined
                request.user.save()

                # Deactivate old user
                user.is_superuser = False
                user.is_staff = False
                user.is_active = False
                user.save()

                return redirect('/user/%s' % request.user.id)

        messages.error(request, _("Username or password is incorrect!"))
    
    return render(request, "home/legacy_login.html", context={})

@login_required(login_url='/login')
def user_settings(request):
    user = request.user
    
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Display name saved successfully."))
        else:
            messages.error(request, _("Enter a valid display name! This value may contain only English letters, "
            "numbers, and @/./+/-/_ characters. Must be between 4-25 characters."))
            return redirect('/user/settings')
    
    return render(request, "home/user_settings.html", context={})
