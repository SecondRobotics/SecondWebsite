from django.db import models
from math import floor

# Create your models here.

class Event(models.Model):
    name = models.CharField(max_length=25)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return self.name

class Player(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=25)

class Ranking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=25)
    ranking_points = models.IntegerField()
    time_set = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ranking - {self.event} - {self.player_name}"

class Match(models.Model):
    MATCH_TYPES = [
        ('q', 'Qualifications'),
        ('qf', 'Quarterfinals'),
        ('sf', 'Semifinals'),
        ('f', 'Finals')]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    match_number = models.IntegerField(null=True, blank=True)
    match_type = models.CharField(max_length=2, choices=MATCH_TYPES, default='q')
    red1 = models.CharField(max_length=25)
    red2 = models.CharField(max_length=25)
    red3 = models.CharField(max_length=25)
    blue1 = models.CharField(max_length=25)
    blue2 = models.CharField(max_length=25)
    blue3 = models.CharField(max_length=25)
    red_score = models.IntegerField(null=True, blank=True)
    red_climb_rp = models.BooleanField(null=True)
    red_wheel_rp = models.BooleanField(null=True)
    blue_score = models.IntegerField(null=True, blank=True)
    blue_climb_rp = models.BooleanField(null=True)
    blue_wheel_rp = models.BooleanField(null=True)

    @property
    def match_name(self):
        if self.match_type == 'q':
            return "Quals " + str(self.match_number)
        elif self.match_type == 'qf':
            series = floor((self.match_number - 1) / 3 + 1)
            match = ((self.match_number - 1) % 3) + 1
            return "Quarters " + str(series) + " Match " + str(match)
        elif self.match_type == 'sf':
            series = floor((self.match_number - 1) / 3 + 1)
            match = ((self.match_number - 1) % 3) + 1
            return "Semis " + str(series) + " Match " + str(match)
        elif self.match_type == 'f':
            return "Finals " + str(self.match_number)
    
    def __str__(self):
        return f"{self.event} - {self.match_name}"

class ElimsAlliance(models.Model):
    ADVANCEMENT_LEVELS = [
        ('qf', 'QF'),
        ('sf', 'SF'),
        ('f', 'F'),
        ('w', 'W')]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    alliance_number = models.IntegerField(null=True, blank=True)
    player1 = models.CharField(max_length=25)
    player2 = models.CharField(max_length=25)
    player3 = models.CharField(max_length=25)
    advancement = models.CharField(max_length=25, choices=ADVANCEMENT_LEVELS, default='qf')

    def __str__(self):
        return f"{self.event} - Alliance {self.alliance_number}"
