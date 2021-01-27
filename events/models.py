from django.db import models
from django.urls import reverse

from rest_framework.reverse import reverse as api_reverse

# Create your models here.

class Event(models.Model):
    name = models.CharField(max_length=25)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return self.name
    

    def get_api_url(self, request=None):
        return api_reverse("api-events:event-rud", kwargs={'pk': self.pk}, request=request)

class Player(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=25)

class Ranking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=25)
    ranking_points = models.IntegerField()
    time_set = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ranking - {self.event}"

class Match(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    match_number = models.IntegerField(null=True, blank=True)
    red1 = models.CharField(max_length=25)
    red2 = models.CharField(max_length=25)
    red3 = models.CharField(max_length=25)
    blue1 = models.CharField(max_length=25)
    blue2 = models.CharField(max_length=25)
    blue3 = models.CharField(max_length=25)
    red_score = models.IntegerField(null=True, blank=True)
    blue_score = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Match - {self.event}"