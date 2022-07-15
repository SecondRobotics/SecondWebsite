from django.urls import path
from . import views

app_name = 'ranked-api'

urlpatterns = [
    path('', views.get_status, name='get-status'),
    path('<str:game_mode_code>/', views.get_game_mode_status, name='get_game_mode_status'),
]
