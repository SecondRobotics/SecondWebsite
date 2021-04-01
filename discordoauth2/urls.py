from django.urls import path

from . import views

urlpatterns = [
    path("", views.get_authenticated_user, name="oauth2"),
    path("login/", views.discord_login, name="oauth2 login"),
    path("login/redirect/", views.discord_login_redirect, name="oauth2 login redirect"),
]
