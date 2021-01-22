from django.shortcuts import render
from .models import Event, Player

# Create your views here.

def event_summary(response):
    events = Event.objects.all()
    context = []
    for event in events:
        players = Player.objects.filter(event__name=event.name)
        print(len(players))
        context.append({"player_num": len(players), "event": event})
    return render(response, "events/event_summary.html", {"context": context})

def robot_event(response, event_name):
    players = Player.objects.filter(event__name=event_name).order_by("player_name")
    print(players)
    num = []
    i = 1 
    for player in players:
        num.append(i)
        i += 1 
    return render(response, "events/event.html", {"event_name": event_name, "players": players, "num": num})