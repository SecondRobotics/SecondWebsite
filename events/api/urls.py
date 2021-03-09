from .views import EventsRudView, EventsAPIView

from django.urls import path

app_name = "api-events"


urlpatterns = [
    path('create/', EventsAPIView.as_view(), name="event-create"),
    path('<int:pk>/', EventsRudView.as_view(), name="event-rud"),
]
