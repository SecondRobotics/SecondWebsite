from django.urls import path
from . import views


urlpatterns = [
    path("", views.event_summary, name="event_summary"),
    path("<str:event_name>/", views.robot_event_tabless, name="robot_event"),
    path("<str:event_name>/<str:tab>", views.robot_event, name="robot_event"),
    path("championship-points/", views.championship_points, name="championship_points"),
]
