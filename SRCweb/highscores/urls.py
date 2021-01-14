from django.urls import path
from . import views


urlpatterns = [
    path("submit/", views.submit, name="submit"),
    path("<str:name>/", views.index, name="index"),
    
]
