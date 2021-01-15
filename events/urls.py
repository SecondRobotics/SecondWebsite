from django.urls import path
from . import views


urlpatterns = [
    path("event1/", views.index, name="submit"),
]
