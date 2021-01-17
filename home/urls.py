from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("about/", views.about, name="about"),
    path("rules/", views.rules, name="rules"),
    path("SRCrules/", views.SRCrules, name="SRCrules"),
    path("STCrules/", views.STCrules, name="STCrules"),
    path("MRCrules/", views.MRCrules, name="MRCrules"),
    path("register/", views.registerPage, name="register"),
    path("login/", views.loginPage, name="login"),
    path("logout/", views.logoutUser, name="logout"),
]
