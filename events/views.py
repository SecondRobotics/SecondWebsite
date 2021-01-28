from django.shortcuts import render
from .models import ElimsAlliance, Event, Player, Match, Ranking

# Create your views here.

def event_summary(response):
    events = Event.objects.all()
    context = []
    for event in events:
        players = Player.objects.filter(event__name=event.name)
        print(len(players))
        context.append({"player_num": len(players), "event": event})

    return render(response, "events/event_summary.html", {"context": context})

def robot_event(response, event_name, tab):
    players = Player.objects.filter(event__name=event_name).order_by("player_name")
    print(players)
    num = []
    i = 1 
    for player in players:
        num.append(i)
        i += 1 

    matches = Match.objects.filter(event__name=event_name)
    quals = matches.filter(match_type='q').order_by('match_number')
    quarters = matches.filter(match_type='qf').order_by('match_number')
    semis = matches.filter(match_type='sf').order_by('match_number')
    finals = matches.filter(match_type='f').order_by('match_number')

    rankings = Ranking.objects.filter(event__name=event_name).order_by('-ranking_points')

    alliances = ElimsAlliance.objects.filter(event__name=event_name).order_by('alliance_number')

    return render(response, "events/event.html", {"event_name": event_name, "tab": tab, "players": players, "num": num, "quals": quals, "quarters": quarters, "semis": semis, "finals": finals, "rankings": rankings, "alliances": alliances})

def robot_event_tabless(response, event_name):
    return robot_event(response, event_name, '')