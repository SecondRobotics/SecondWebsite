from datetime import datetime
from rest_framework.test import APITestCase
from events.models import Event
from datetime import datetime
from rest_framework import status

from rest_framework.reverse import reverse as api_reverse

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

    # Test would do something if perms were allowed.

    # def test_get_event(self):
    #     data = {}
    #     url = api_reverse("api-events:event-create")
    #     response = self.client.get(url, data, format="json")
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)