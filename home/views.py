from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(response):
    return render(response, "home/home.html", {})

def two(response):
    return render(response, "home/base.html", {})

def about(response):
    return render(response, "home/about.html", {})