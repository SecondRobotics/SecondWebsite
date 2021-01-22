from django.shortcuts import render
from .models import Event, Player

# Create your views here.

def event_summary(response):
    events = Event.objects.all()
    return render(response, "events/event_summary.html", {"events": events})

def robot_event(response, event_name):
    players = Player.objects.filter(event__name=event_name).order_by("player_name")
    print(players)
    num = []
    i = 1 
    for player in players:
        num.append(i)
        i += 1 
    return render(response, "events/event.html", {"event_name": event_name, "players": players, "num": num})