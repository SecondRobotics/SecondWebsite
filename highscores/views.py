from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.http import HttpResponse
from .models import Leaderboard, Score
from datetime import datetime
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail, BadHeaderError
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max, Q

from django.conf import settings

from .forms import ScoreForm


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
            
            obj.save()
            message = f"{obj.player_name} [{form.cleaned_data['score']}] - {form.cleaned_data['leaderboard']}\n\n {form.cleaned_data['source']}\n\nhttps://secondrobotics.org/admin/highscores/score/"
            try:
                send_mail(f"New score from {obj.player_name}", message, "noreply@secondrobotics.org", ['brennan@secondrobotics.org'], fail_silently=False)
            except BadHeaderError:
                return HttpResponse('Invalid header found.')
            return HttpResponseRedirect(f'/highscores/submit-success')
    else:
        form = ScoreForm
    return render(request, "highscores/submit.html", {"form": form})

def submit_success(request):
    return render(request, "highscores/submit_success.html", {})