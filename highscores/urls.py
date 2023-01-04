from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path("<str:game_slug>/submit/", views.submit_form, name="score submit"),
    path("<str:game_slug>/combined/", views.leaderboard_combined,
         name="game leaderboard"),
    path("<str:game_slug>/<str:name>/",
         views.leaderboard_robot, name="robot leaderboard"),
]
