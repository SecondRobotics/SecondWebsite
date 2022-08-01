from django.urls import path
from . import views


urlpatterns = [
    path('', views.ranked_home, name='home'),
    path('<str:name>/', views.leaderboard, name='leaderboard'),
    path('<str:name>/<str:player_name>', views.player_info, name='player_info'),
]
