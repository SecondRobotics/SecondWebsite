from rest_framework import serializers
from events.models import Event

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'pk',
            'name',
            'start_time',
            'end_time',
        ]
    # Converts to JSON
    # Validates data