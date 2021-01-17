from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.http import HttpResponse
from .models import Leaderboard, Score
from datetime import datetime
from django.core.files.storage import FileSystemStorage

from .forms import ScoreForm

from django.conf import settings
# file._size > settings.MAX_UPLOAD_SIZE

# Create your views here.

def index(response, name):
    # ls = Leaderboard.objects.get(name=name)
    sorted = Score.objects.filter(leaderboard__name=name, approved=True).order_by('-score', 'time_set')
    i = 1
    context = []
    # Create ranking numbers and append them to sorted values
    for item in sorted:
        context.append([i, item])
        i+=1

    return render(response, "highscores/leaderboard_ranks.html", {"ls": context, "robot_name":name})

def submit(request):
    if request.method == "POST":
        # uploaded_file = request.FILES.get('score-screenshot', False)
        form = ScoreForm(request.POST)
        if form.is_valid():
            # fs = FileSystemStorage()
            # fs.save(uploaded_file.name, uploaded_file)
            obj = Score()
            obj.leaderboard = form.cleaned_data['leaderboard']
            obj.player_name = form.cleaned_data['player_name']
            obj.score = form.cleaned_data['score']
            obj.time_set = datetime.now()
            obj.approved = False
            obj.source = form.cleaned_data['source']
            
            obj.save()
        return HttpResponseRedirect(f'/highscores/submit-success')
    else:
        form = ScoreForm
    return render(request, "highscores/submit.html", {"form": form})

def submit_success(request):
    return render(request, "highscores/submit_success.html", {})