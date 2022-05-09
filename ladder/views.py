from django.db.models import Q
from django.shortcuts import render
from .models import *

# Create your views here.

def index(response):
    
    divisions = Division.objects.all()

    week1_divisions = divisions.filter(week=1).order_by('level')
    week2_divisions = divisions.filter(week=2)
    week3_divisions = divisions.filter(week=3)
    week4_divisions = divisions.filter(week=4)
    week5_divisions = divisions.filter(week=5)

    context = {'week1_divisions': week1_divisions, 'week2_divisions': week2_divisions, 'week3_divisions': week3_divisions, 'week4_divisions': week4_divisions, 'week5_divisions': week5_divisions}


    return render(response, "ladder/index.html", context=context)

def division(response, week, division):

    try:
        division = Division.objects.get(week=week, level=division)
    except:
        return render(response, "ladder/division_error.html")
    
    context = {'division': division, 'schedule': division.get_prepared_schedule()}

    return render(response, "ladder/division_detail.html", context=context)