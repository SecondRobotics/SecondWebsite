from .views import EventsRudView

from django.urls import path

app_name = "api-events"


urlpatterns = [
    path('<int:pk>/', EventsRudView.as_view(), name="event-rud"),
]
