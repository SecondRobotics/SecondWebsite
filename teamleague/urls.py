from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("<str:team_code>", views.team_page, name="team_page")
]
