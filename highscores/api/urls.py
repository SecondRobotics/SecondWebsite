from django.urls import path
from . import views

app_name = 'highscores-api'

urlpatterns = [
    path('', views.get_session_validity, name='get_session_validity'),
    path('auth/', views.auth, name='auth'),
    path('submit/', views.submit, name='submit'),
]
