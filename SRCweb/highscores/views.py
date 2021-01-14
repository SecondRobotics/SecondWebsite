from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.http import HttpResponse
from .models import Leaderboard, Score

from .forms import SubmitScore

# Create your views here.

def index(response, name):
    # ls = Leaderboard.objects.get(name=name)
    sorted = Score.objects.filter(leaderboard__name=name).order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted:
        context.append([i, item])
        i+=1

    return render(response, "highscores/leaderboard_ranks.html", {"ls": context, "robot_name":name})

def submit(response):
    if response.method == "POST":
        form = SubmitScore(response.POST)
        if form.is_valid():
            n = form.cleaned_data['name']
            t = Leaderboard(name=n)
            t.save()
        return HttpResponseRedirect(f'/highscores/{t.name}')
    else:
        form = SubmitScore
    return render(response, "highscores/submit.html", {"form": form})