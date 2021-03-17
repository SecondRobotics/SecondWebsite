from django.db import models
from django.db.models import Window, F, Count
from django.db.models.functions import Rank
from django.contrib.auth.models import User

# Create your models here.

class Alliance(models.Model):
    key = models.CharField(max_length=25)

    name = models.CharField(max_length=25)

    player1 = models.CharField(max_length=25)
    player1_user = models.OneToOneField(User, null=True, blank=True, on_delete=models.PROTECT, related_name='player1_users')
    
    player2 = models.CharField(max_length=25)
    player2_user = models.OneToOneField(User, null=True, blank=True, on_delete=models.PROTECT, related_name='player2_users')
    
    player3 = models.CharField(max_length=25)
    player3_user = models.OneToOneField(User, null=True, blank=True, on_delete=models.PROTECT, related_name='player3_users')

    wins = models.IntegerField(null=True, blank=True)
    tiebreaker = models.IntegerField(null=True, blank=True)
    differential = models.IntegerField(null=True, blank=True)
    total_points = models.IntegerField(null=True, blank=True)

    logo = models.URLField(default="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRI7M4Z0v1HP2Z9tZmfQaZFCuspezuoxter_A&usqp=CAU")
    primary_color = models.CharField(max_length=6, default='999999')
    secondary_color = models.CharField(max_length=6, default='222222')

    def __str__(self):
        return self.name


class Matchup(models.Model):
    week = models.IntegerField()

    red_alliance = models.ForeignKey(Alliance, on_delete=models.PROTECT, related_name='red_alliances')
    blue_alliance = models.ForeignKey(Alliance, on_delete=models.PROTECT, related_name='blue_alliances')

    # published = models.BooleanField(default=False)

    def get_red_wins(self):
        red_wins = 0

        if self.match_1_red != None and self.match_1_blue != None:
            if self.match_1_red > self.match_1_blue:
                red_wins += 1

        if self.match_2_red != None and self.match_2_blue != None:
            if self.match_2_red > self.match_2_blue:
                red_wins += 1

        if self.match_3_red != None and self.match_3_blue != None:
            if self.match_3_red > self.match_3_blue:
                red_wins += 1

        if self.match_4_red != None and self.match_4_blue != None:
            if self.match_4_red > self.match_4_blue:
                red_wins += 1

        if self.match_5_red != None and self.match_5_blue != None:
            if self.match_5_red > self.match_5_blue:
                red_wins += 1

        if self.match_6_red != None and self.match_6_blue != None:
            if self.match_6_red > self.match_6_blue:
                red_wins += 1

        if self.match_7_red != None and self.match_7_blue != None:
            if self.match_7_red > self.match_7_blue:
                red_wins += 1

        return red_wins

    def get_blue_wins(self):
        blue_wins = 0
        if self.match_1_red != None and self.match_1_blue != None:
            if self.match_1_red < self.match_1_blue:
                blue_wins += 1

        if self.match_2_red != None and self.match_2_blue != None:
            if self.match_2_red < self.match_2_blue:
                blue_wins += 1

        if self.match_3_red != None and self.match_3_blue != None:
            if self.match_3_red < self.match_3_blue:
                blue_wins += 1

        if self.match_4_red != None and self.match_4_blue != None:
            if self.match_4_red < self.match_4_blue:
                blue_wins += 1

        if self.match_5_red != None and self.match_5_blue != None:
            if self.match_5_red < self.match_5_blue:
                blue_wins += 1

        if self.match_6_red != None and self.match_6_blue != None:
            if self.match_6_red < self.match_6_blue:
                blue_wins += 1

        if self.match_7_red != None and self.match_7_blue != None:
            if self.match_7_red < self.match_7_blue:
                blue_wins += 1

        return blue_wins

    def winner(self):
        if self.get_red_wins() >= 4:
            return 'r'
        elif self.get_blue_wins() >= 4:
            return 'b'
        else:
            return 'u'

    def get_red_total_score(self):
        return int(self.match_1_red or 0) + int(self.match_2_red or 0) + int(self.match_3_red or 0) + int(self.match_4_red or 0) + int(self.match_5_red or 0) + int(self.match_6_red or 0) + int(self.match_7_red or 0)
    
    def get_blue_total_score(self):
        return int(self.match_1_blue or 0) + int(self.match_2_blue or 0) + int(self.match_3_blue or 0) + int(self.match_4_blue or 0) + int(self.match_5_blue or 0) + int(self.match_6_blue or 0) + int(self.match_7_blue or 0)

    match_1_red = models.IntegerField(null=True, blank=True)
    match_1_blue = models.IntegerField(null=True, blank=True)

    match_2_red = models.IntegerField(null=True, blank=True)
    match_2_blue = models.IntegerField(null=True, blank=True)

    match_3_red = models.IntegerField(null=True, blank=True)
    match_3_blue = models.IntegerField(null=True, blank=True)

    match_4_red = models.IntegerField(null=True, blank=True)
    match_4_blue = models.IntegerField(null=True, blank=True)

    match_5_red = models.IntegerField(null=True, blank=True)
    match_5_blue = models.IntegerField(null=True, blank=True)

    match_6_red = models.IntegerField(null=True, blank=True)
    match_6_blue = models.IntegerField(null=True, blank=True)

    match_7_red = models.IntegerField(null=True, blank=True)
    match_7_blue = models.IntegerField(null=True, blank=True)

    @property
    def show_match_5(self):
        return (self.get_red_wins() + self.get_blue_wins() >= 4 and self.winner() == 'u') or self.get_red_wins() + self.get_blue_wins() >= 5

    @property
    def show_match_6(self):
        return (self.get_red_wins() + self.get_blue_wins() >= 5 and self.winner() == 'u') or self.get_red_wins() + self.get_blue_wins() >= 6

    @property
    def show_match_7(self):
        return (self.get_red_wins() + self.get_blue_wins() >= 6 and self.winner() == 'u') or self.get_red_wins() + self.get_blue_wins() >= 7

    def __str__(self):
        return "Week " + str(self.week) + " - " + self.red_alliance.name + " vs " + self.blue_alliance.name
    
    def save(self, *args, **kwargs):
        super(Matchup, self).save(*args, **kwargs)
        calculate_rankings()

def calculate_rankings():
    teams = Alliance.objects.all()
    matchups = Matchup.objects.all()

    for team in teams:
        red_matchups = matchups.filter(red_alliance=team)
        blue_matchups = matchups.filter(blue_alliance=team)

        wins = 0
        differential = 0
        total_points = 0

        for matchup in red_matchups:

            if matchup.winner() == 'r':
                wins += 1
            
            differential += (matchup.get_red_total_score() - matchup.get_blue_total_score())

            total_points += matchup.get_red_total_score()
        
        for matchup in blue_matchups:

            if matchup.winner() == 'b':
                wins += 1
            
            differential += (matchup.get_blue_total_score() - matchup.get_red_total_score())

            total_points += matchup.get_blue_total_score()

        team.wins = wins
        team.tiebreaker = None
        team.differential = differential
        team.total_points = total_points
        team.save()
    
    teams = Alliance.objects.all()


    duplicates = teams.values('wins').annotate(count=Count('wins')).filter(count__gt=1)
    for count in duplicates:
        wins = count['wins']
        if wins == 0:
            continue
        tied_teams = teams.filter(wins=wins)

        matchups = Matchup.objects.filter(red_alliance__in=tied_teams, blue_alliance__in=tied_teams)

        for team in tied_teams:
            red_matchups = matchups.filter(red_alliance=team)
            blue_matchups = matchups.filter(blue_alliance=team)

            tiebreaker = 0

            for matchup in red_matchups:
                if matchup.winner() == 'r':
                    tiebreaker += 1
            
            for matchup in blue_matchups:
                if matchup.winner() == 'b':
                    tiebreaker += 1
            
            team.tiebreaker = tiebreaker
            team.save()

    Alliance.objects.filter(tiebreaker=None).update(tiebreaker=0)
