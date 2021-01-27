from rest_framework import serializers
from events.models import Event

class EventSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Event
        fields = [
            'url',
            'name',
            'start_time',
            'end_time',
        ]

    # Converts to JSON
    # Validates data

    def get_url(self, obj):
        request = self.context.get("request")
        return obj.get_api_url(request=request)

    def validate_name(self, value):
        qs = Event.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("The event name has already been used")
        return value