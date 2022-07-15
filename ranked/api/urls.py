from django.urls import path
from . import views

app_name = 'ranked-api'

urlpatterns = [
    path('', views.get_status, name='get-status'),
    path('<str:game_mode_code>/', views.get_game_mode, name='get_game_mode'),
    path('<str:game_mode_code>/player/<str:player_id>/',
         views.get_player_stats, name='get_player_stats'),
    path('<str:game_mode_code>/player/<str:player_id>/history/',
         views.get_player_elo_history, name='get_player_elo_history'),
]
