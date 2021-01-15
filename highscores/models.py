from django.db import models

# Create your models here.

class Leaderboard(models.Model):
    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name

class Score(models.Model):
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=25)
    score = models.IntegerField()
    time_set = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(default=False, null=False)

    def __str__(self):
        return f"{self.player_name} - {self.leaderboard} [{self.score}]"