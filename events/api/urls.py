from .views import EventsRudView

from django.urls import path


urlpatterns = [
    path(r'^(?P<pk>\d+)/$', EventsRudView, name="event-rud"),
]
