from datetime import datetime
from rest_framework.test import APITestCase
from events.models import Event
from datetime import datetime

class EventAPITestCase(APITestCase):
    def setUp(self):
        event = Event.objects.create(
            name="Event_Name", 
            start_time=datetime.now(), 
            end_time=datetime.now()
            )

    def test_single_event(self):
        event_count = Event.objects.count()
        self.assertEqual(event_count, 1)