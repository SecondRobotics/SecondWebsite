from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path("ir/submit/", views.infinite_recharge_submit_form, name="IR submit"),
    path("rr/submit/", views.rapid_react_submit_form, name="RR submit"),
    path("ff/submit/", views.freight_frenzy_submit_form, name="FF submit"),
    path("tp/submit/", views.tipping_point_submit_form, name="TP submit"),
    path("su/submit/", views.spin_up_submit_form, name="SU submit"),
    path("ir/combined/", views.infinite_recharge_combined, name="IR combined"),
    path("rr/combined/", views.rapid_react_combined, name="RR combined"),
    path("ff/combined/", views.freight_frenzy_combined, name="FF combined"),
    path("ir/<str:name>/", views.leaderboard_index, name="IR leaderboard"),
    path("rr/<str:name>/", views.leaderboard_index, name="RR leaderboard"),
    path("ff/<str:name>/", views.leaderboard_index, name="FF leaderboard"),
    path("tp/<str:name>/", views.leaderboard_index, name="TP leaderboard"),
    path("su/<str:name>/", views.leaderboard_index, name="SU leaderboard"),
]
