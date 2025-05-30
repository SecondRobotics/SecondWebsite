from django.urls import path
from . import views
from .api import views as api_views


urlpatterns = [
    path('', views.ranked_home, name='home'),
    path('<str:name>/', views.leaderboard, name='leaderboard'),
    path('<str:name>/<str:player_id>', views.player_info, name='player_info'),
    path('info/', views.ranked_info, name='ranked_info'),
    path('api/stats/', api_views.get_stats, name='ranked_stats'),
    path('api/leaderboard/', api_views.get_leaderboard, name='ranked_leaderboard'),
    path('api/recalculate/', api_views.recalculate_elo, name='ranked_recalculate'),
]
