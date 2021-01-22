from django.urls import path
from . import views


urlpatterns = [
    path("", views.event_summary, name="event_summary"),
    path("<str:event_name>/", views.robot_event, name="robot_event"),
]
