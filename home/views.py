from django.http.response import HttpResponseRedirect
from discordoauth2.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, logout
from django.contrib import messages
from django.db.models import Q
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required

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
        if user.exists() and password and len(password) > 3 and user[0].check_password(password) and user[0].is_active:
            # Merge accounts
            for score in Score.objects.filter(player=user[0]):
                score.player = request.user
                score.save()
            for score in CleanCodeSubmission.objects.filter(player=user[0]):
                score.player = request.user
                score.save()
            
            user[0].active = False
            user[0].save()

            return redirect('/user/%s' % request.user.id)
        else:
            messages.info(request, "Username or Password is Incorrect")
    
    context = {}
    return render(request, "home/legacy_login.html", context)

@login_required(login_url='/login')
def user_settings(request):
    user = request.user
    form = ProfileForm(instance=user)
    
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
        else:
            return redirect('/user/settings')
    
    return render(request, "home/user_settings.html", {"form": form, "user": user})
