from django.urls import path
from . import views


urlpatterns = [
    path("<str:eventname>/", views.robot_event, name="robot_event"),
]
