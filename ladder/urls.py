from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("w<int:week>d<int:division>", views.division, name="division")
]
