from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path("ir/submit/", views.infinite_recharge_submit, name="IR submit"),
    path("ir/combined/", views.infinite_recharge_combined, name="IR combined"),
    path("ff/combined/", views.freight_frenzy_combined, name="FF combined"),
    path("ir/<str:name>/", views.leaderboard_index, name="IR leaderboard"),
    path("ff/<str:name>/", views.leaderboard_index, name="FF leaderboard"),
    path("tp/<str:name>/", views.leaderboard_index, name="TP leaderboard"),
]
