from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("about/", views.about, name="about"),
    path("rules/", views.rules, name="rules"),
    path("SRCrules/", views.src_rules, name="SRCrules"),
    path("STCrules/", views.stc_rules, name="STCrules"),
    path("MRCrules/", views.mrc_rules, name="MRCrules"),
    path("register/", views.register_page, name="register"),
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("user/<str:username>/", views.user_profile, name="userprofile"),
    path("discord/", views.discord, name="discord"),
]
