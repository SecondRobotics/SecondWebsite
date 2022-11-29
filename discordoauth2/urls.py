from django.urls import path

from . import views

urlpatterns = [
    path("", views.get_authenticated_user, name="oauth2"),
    path("login/", views.discord_login, name="oauth2 login"),
    path("loginapi/", views.discord_api_login, name="oauth2 login with api"),
    path("login/redirect/", views.discord_login_redirect,
         name="oauth2 login redirect"),
    path("loginapi/redirect/", views.discord_api_login_redirect,
         name="oauth2 login with api redirect"),
]
