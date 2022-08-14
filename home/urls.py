from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("about/", views.about, name="about"),
    path("mrc/", views.mrc, name="mrc"),
    path("rules/", views.rules, name="rules"),
    path("staff/", views.staff, name="staff"),
    path("SRCrules/", views.src_rules, name="SRC rules"),
    path("STCrules/", views.stc_rules, name="STC rules"),
    path("MRCrules/", views.mrc_rules, name="MRC rules"),
    path("SVCrules/", views.svc_rules, name="SVC rules"),
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("reauth/", views.reauth_user, name="reauthenticate user"),
    path("user/settings/", views.user_settings, name="user settings"),
    # path("legacy-merge/", views.merge_legacy_account, name="merge legacy account"),
    path("user/<int:user_id>/", views.user_profile, name="user profile"),
    path("discord/", views.discord, name="discord"),
    path("hall-of-fame/", views.hall_of_fame, name="hall of fame"),
    path("merch/", views.merch, name="merch"),
    path("privacy/", views.privacy, name="privacy"),
    path("logopack/", views.logos, name="logos"),
]
