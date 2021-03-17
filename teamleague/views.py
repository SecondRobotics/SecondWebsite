from django.db.models import Q
from django.shortcuts import render
from .models import *

# Create your views here.


def index(response):
    alliances = Alliance.objects.annotate(
        rank=Window(expression=Rank(),
            order_by=[F("wins").desc(), F("tiebreaker").desc(), F("differential").desc(), F("total_points").desc()]
        )
    ).order_by("rank")

    matchups = Matchup.objects.all()

    week1_matchups = matchups.filter(week=1)
    week2_matchups = matchups.filter(week=2)
    week3_matchups = matchups.filter(week=3)
    week4_matchups = matchups.filter(week=4)
    week5_matchups = matchups.filter(week=5)

    context = {'alliances': alliances, 'week1_matchups': week1_matchups, 'week2_matchups': week2_matchups, 'week3_matchups': week3_matchups, 'week4_matchups': week4_matchups, 'week5_matchups': week5_matchups}
    return render(response, "teamleague/index.html", context)

def team_page(response, team_code):
    team = Alliance.objects.get(key=team_code)

    matchups = Matchup.objects.filter(Q(red_alliance=team) | Q(blue_alliance=team)).order_by('week')

    context = {'team': team, 'matchups':matchups}
    return render(response, "teamleague/team_page.html", context)
