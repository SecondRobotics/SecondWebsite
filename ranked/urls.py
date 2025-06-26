from django.urls import path
from . import views
from .api import views as api_views


urlpatterns = [
    path('', views.ranked_home, name='home'),
    path('info/', views.ranked_info, name='ranked_info'),
    path('<str:name>/', views.leaderboard, name='leaderboard'),
    path('<str:name>/<str:player_id>', views.player_info, name='player_info'),
]
