from django.shortcuts import render
from .models import Event

# Create your views here.

def event_summary(response):
    return render(response, "events/event_summary.html", {})

def robot_event(response, eventname):
    return render(response, "events/event.html", {})