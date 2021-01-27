from rest_framework import generics, mixins
from events.models import Event
from .serializers import EventSerializer
from django.db.models import Q
from .permissions import IsOwnerOrReadOnly

class EventsAPIView(mixins.CreateModelMixin, generics.ListAPIView):
    lookup_field = 'pk'
    serializer_class = EventSerializer
    queryset = Event.objects.all()

    def get_queryset(self):
        qs = Event.objects.all()
        query = self.request.GET.get('q')
        if query is not None:
            qs = qs.filter(name__icontains=query)
        return qs

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class EventsRudView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = 'pk'
    serializer_class = EventSerializer
    queryset = Event.objects.all()

    def get_queryset(self):
        return Event.objects.all()