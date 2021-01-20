from django.urls import path
from . import views


urlpatterns = [
    path("submit/", views.submit, name="submit"),
    path("combined/", views.combined, name="combined"),
    path("submit-success/", views.submit_success, name="success!"),
    path("<str:name>/", views.index, name="index"),
]
