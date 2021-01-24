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
    source = models.URLField(null=False, blank=False)
    approved = models.BooleanField(default=False, null=False)
    clean_code = models.CharField(max_length=400, null=True, blank=True)
    
    decrypted_code = models.CharField(max_length=400, null=True, blank=True)
    client_version = models.CharField(max_length=20, null=True, blank=True)
    time_of_score = models.CharField(max_length=20, null=True, blank=True)
    robot_position = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.player_name} - {self.leaderboard} [{self.score}]"