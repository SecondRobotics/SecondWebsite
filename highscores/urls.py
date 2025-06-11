from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    #     path("<str:game_slug>/submit/", views.submit_form, name="score submit"),
    path("<str:game_slug>/combined/", views.leaderboard_combined,
         name="game leaderboard"),
    path("<str:game_slug>/<str:name>/",
         views.leaderboard_robot, name="robot leaderboard"),
     path('world-records/', views.world_records, name='world-records'),
     path('overall/', views.overall_singleplayer_leaderboard, name='overall-singleplayer-leaderboard'),
     path('webhook-test/', views.webhook_test, name='webhook-test'),
]
