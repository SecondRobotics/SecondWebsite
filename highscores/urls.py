from django.urls import path
from . import views


urlpatterns = [
    path("submit/", views.submit, name="submit"),
    path("combined/", views.combined, name="combined"),
    path("<str:name>/", views.index, name="index"),
]
