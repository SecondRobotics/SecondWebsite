from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("about/", views.about, name="home"),
    path("register/", views.registerPage, name="home"),
    path("login/", views.loginPage, name="home"),
    path("logout/", views.logoutUser, name="home"),
]
