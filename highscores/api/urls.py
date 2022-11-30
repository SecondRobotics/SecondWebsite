from django.urls import path
from . import views

app_name = 'highscores-api'

urlpatterns = [
    path('', views.get_session_validity, name='get_session_validity'),
    path('auth/', views.auth, name='auth'),
    path('submit/', views.submit, name='submit'),
    path('my_scores/', views.get_my_scores, name='get_my_scores'),
    path('leaderboard/<str:game_slug>/',
         views.get_leaderboard, name='get_leaderboard'),
    path('leaderboards/', views.get_leaderboards, name='get_leaderboards'),
]
