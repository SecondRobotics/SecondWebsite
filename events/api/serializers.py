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

    def validate_name(self, value):
        qs = Event.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("The event name has already been used")
        return value