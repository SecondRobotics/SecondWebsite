from django.shortcuts import render, redirect
from django.http import HttpResponse, request
from django.contrib.auth.forms import UserCreationForm
from .forms import CreateUserForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

from highscores.models import Leaderboard, Score

def index(response):
    print(response.user)
    return render(response, "home/home.html", {})

def about(response):
    return render(response, "home/about.html", {})

def rules(response):
    return render(response, "home/rules.html", {})

def src_rules(response):
    return redirect('https://bit.ly/SRCrules')

def stc_rules(response):
    return redirect('https://bit.ly/STC-rules')

def mrc_rules(response):
    return redirect('https://bit.ly/MRC-rules')

def register_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
        form = CreateUserForm()
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()
                user = form.cleaned_data.get('username')
                messages.success(request, f"Account was created for {user}")
                return redirect('/login')

        context = {"form": form}
        return render(request, "home/register.html", context)

def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
        if request.method == "POST":
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('/')
            else:
                messages.info(request, "Username or Password is Incorrect")
        context = {}
        return render(request, "home/login.html", context)

def logout_user(request):
    logout(request)
    return redirect('/login')

def user_profile(request, username):
    scores = Score.objects.filter(player_name=username)
    context = {"username": username, "overall": 0}
    for score in scores:
        context.update({score.leaderboard.name: score.score})
        context.update({"overall": score.score + context['overall']})
    print(context)
    return render(request, "home/user_profile.html", context)