from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, int_list_validator
from discordoauth2.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.


class GameMode(models.Model):
    name = models.CharField(max_length=25, unique=True)
    game = models.CharField(max_length=25)
    players_per_alliance = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)])
    short_code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Match(models.Model):
    match_number = models.AutoField(primary_key=True)
    time = models.DateTimeField(auto_now_add=True)
    game_mode = models.ForeignKey(GameMode, on_delete=models.CASCADE)

    red_alliance = models.ManyToManyField(User, related_name="red_alliance")
    blue_alliance = models.ManyToManyField(User, related_name="blue_alliance")

    red_score = models.IntegerField()
    blue_score = models.IntegerField()

    red_starting_elo = models.FloatField()
    blue_starting_elo = models.FloatField()

    def get_red_players(self):
        return self.red_alliance.all()

    def get_blue_players(self):
        return self.blue_alliance.all()

    def __str__(self):
        return f"{self.match_number} - {self.game_mode} - {self.time}"


class PlayerElo(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    game_mode = models.ForeignKey(GameMode, on_delete=models.CASCADE)

    elo = models.FloatField(default=1200)

    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    matches_drawn = models.IntegerField(default=0)
    last_match_played_time = models.DateTimeField(null=True, blank=True)
    last_match_played_number = models.IntegerField(null=True, blank=True)
    total_score = models.IntegerField(default=0)

    @property
    def win_rate(self):
        if self.matches_played == 0:
            return 0
        else:
            return self.matches_won / self.matches_played * 100

    def __str__(self):
        return f"{self.player} - {self.game_mode} - {self.elo}"


class EloHistory(models.Model):
    player_elo = models.ForeignKey(PlayerElo, on_delete=models.CASCADE)
    match_number = models.IntegerField()
    elo = models.FloatField()

    def __str__(self):
        return f"{self.player_elo.player} - {self.match_number}"
