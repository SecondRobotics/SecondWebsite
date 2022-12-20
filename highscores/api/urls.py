from django.urls import path
from . import views

app_name = 'highscores-api'

urlpatterns = [
    path('', views.get_session_validity, name='get_session_validity'),
    path('auth/', views.auth, name='auth'),
    path('submit/', views.submit, name='submit'),
    path('scores/', views.get_my_scores, name='get_my_scores'),
    path('scores/<int:user_id>/', views.get_player_scores,
         name='get_player_scores'),
    path('leaderboard/', views.get_leaderboards, name='get_all_leaderboards'),
    path('leaderboard/game/<str:game>/',
         views.get_game_leaderboards, name='get_leaderboards_by_game'),
    path('leaderboard/robot/<str:robot>/',
         views.get_robot_leaderboard, name='get_leaderboard_by_robot'),
    path('leaderboard/name/<str:leaderboard>/',
         views.get_leaderboard, name='get_leaderboard_by_name'),
]
