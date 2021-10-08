from discordoauth2.models import User
from django.db import models

# Create your models here.


class Leaderboard(models.Model):
    name = models.CharField(max_length=25)  # robot type
    game = models.CharField(max_length=25)  # game

    def __str__(self):
        return self.name


class Score(models.Model):
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE)
    player = models.ForeignKey(User, on_delete=models.CASCADE)

    score = models.IntegerField()
    time_set = models.DateTimeField(null=True, blank=True)
    source = models.URLField(null=False, blank=False)
    approved = models.BooleanField(default=False, null=False)
    clean_code = models.CharField(max_length=600, null=False, blank=False)

    decrypted_code = models.CharField(max_length=600, null=True, blank=True)
    client_version = models.CharField(max_length=20, null=True, blank=True)
    time_of_score = models.CharField(max_length=30, null=True, blank=True)
    robot_position = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.player} - {self.leaderboard} [{self.score}]"


class CleanCodeSubmission(models.Model):
    clean_code = models.CharField(max_length=600)
    player = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.clean_code
