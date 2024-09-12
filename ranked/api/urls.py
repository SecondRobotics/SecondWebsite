from django.urls import path
from . import views

app_name = 'ranked-api'

urlpatterns = [
    path('', views.ranked_api, name='ranked_api'),
    path('all-users/', views.get_all_users, name='get_all_users'),  # Changed from 'users/' to 'all-users/'
    path('player/<str:player_id>/', views.get_player, name='get_player'),
    path('<str:game_mode_code>/', views.get_game_mode, name='get_game_mode'),
    path('<str:game_mode_code>/player/<str:player_id>/', views.get_player_stats, name='get_player_stats'),
    path('<str:game_mode_code>/player/<str:player_id>/history/', views.get_player_elo_history, name='get_player_elo_history'),
    path('<str:game_mode_code>/match/', views.post_match_result, name='post_match_result'),
    path('<str:game_mode_code>/match/edit/', views.edit_match_result, name='edit_match_result'),
    path('leaderboard/<str:game_mode_code>/', views.get_leaderboard, name='get_leaderboard'),
    path('<str:game_mode_code>/players/', views.get_valid_players, name='get_valid_players'),
]
