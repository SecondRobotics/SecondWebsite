from discordoauth2.models import User
from django.db import models

# Create your models here.


class Leaderboard(models.Model):
    name = models.CharField(max_length=25)  # "informal" robot name
    robot = models.CharField(max_length=25)  # in-game robot name

    game = models.CharField(max_length=25)
    game_slug = models.CharField(max_length=5)
    auto_or_teleop = models.CharField(
        max_length=4, default="TELE")

    message = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.name


class Score(models.Model):
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE)
    player = models.ForeignKey(User, on_delete=models.CASCADE)

    score = models.IntegerField()
    time_set = models.DateTimeField(auto_now_add=True)
    source = models.URLField(null=False, blank=False)
    approved = models.BooleanField(default=False, null=False)
    clean_code = models.CharField(max_length=600, null=False, blank=False)

    decrypted_code = models.CharField(max_length=600, null=True, blank=True)
    client_version = models.CharField(max_length=20, null=True, blank=True)
    time_of_score = models.CharField(max_length=30, null=True, blank=True)
    robot_position = models.CharField(max_length=20, null=True, blank=True)
    time_data = models.TextField(null=True, blank=True)
    ip = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['leaderboard']),
            models.Index(fields=['player']),
            models.Index(fields=['approved']),
        ]

    def __str__(self):
        return f"{self.player} - {self.leaderboard} [{self.score}]"


class CleanCodeSubmission(models.Model):
    clean_code = models.CharField(max_length=600)
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE)
    time_set = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.clean_code

