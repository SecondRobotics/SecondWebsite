from rest_framework import generics
from events.models import Event
from .serializers import EventSerializer

class EventsAPIView(generics.CreateAPIView):
    lookup_field = 'pk'
    serializer_class = EventSerializer
    queryset = Event.objects.all()

    def get_queryset(self):
        return Event.objects.all()

class EventsRudView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'pk'
    serializer_class = EventSerializer
    queryset = Event.objects.all()

    def get_queryset(self):
        return Event.objects.all()