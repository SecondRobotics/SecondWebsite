from django.db import models
from SRCweb import settings
import copy

# Create your models here.

class Division(models.Model):
    week = models.IntegerField(null=False,blank=False)

    level = models.IntegerField(null=False,blank=False)

    complete = models.BooleanField(default=False)

    player1 = models.CharField(max_length=25,null=True,blank=True)
    player2 = models.CharField(max_length=25,null=True,blank=True)
    player3 = models.CharField(max_length=25,null=True,blank=True)
    player4 = models.CharField(max_length=25,null=True,blank=True)
    player5 = models.CharField(max_length=25,null=True,blank=True)
    player6 = models.CharField(max_length=25,null=True,blank=True)

    player1_absent = models.BooleanField(default=False)
    player2_absent = models.BooleanField(default=False)
    player3_absent = models.BooleanField(default=False)
    player4_absent = models.BooleanField(default=False)
    player5_absent = models.BooleanField(default=False)
    player6_absent = models.BooleanField(default=False)

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

    match_8_red = models.IntegerField(null=True, blank=True)
    match_8_blue = models.IntegerField(null=True, blank=True)

    match_9_red = models.IntegerField(null=True, blank=True)
    match_9_blue = models.IntegerField(null=True, blank=True)

    match_10_red = models.IntegerField(null=True, blank=True)
    match_10_blue = models.IntegerField(null=True, blank=True)

    match_11_red = models.IntegerField(null=True, blank=True)
    match_11_blue = models.IntegerField(null=True, blank=True)

    match_12_red = models.IntegerField(null=True, blank=True)
    match_12_blue = models.IntegerField(null=True, blank=True)

    match_13_red = models.IntegerField(null=True, blank=True)
    match_13_blue = models.IntegerField(null=True, blank=True)

    match_14_red = models.IntegerField(null=True, blank=True)
    match_14_blue = models.IntegerField(null=True, blank=True)

    match_15_red = models.IntegerField(null=True, blank=True)
    match_15_blue = models.IntegerField(null=True, blank=True)

    @property
    def num_players(self):
        count = 0
        count += 0 if self.player1 == None or self.player1_absent == True else 1
        count += 0 if self.player2 == None or self.player2_absent == True else 1
        count += 0 if self.player3 == None or self.player3_absent == True else 1
        count += 0 if self.player4 == None or self.player4_absent == True else 1
        count += 0 if self.player5 == None or self.player5_absent == True else 1
        count += 0 if self.player6 == None or self.player6_absent == True else 1
        return count

    # @property
    def get_schedule(self):
        if self.num_players == 6:
            return SIX_PLAYER_SCHEDULE
        elif self.num_players == 5:
            return FIVE_PLAYER_SCHEDULE
        else:
            return FOUR_PLAYER_SCHEDULE

    
    def save(self, *args, **kwargs):
        super(Division, self).save(*args, **kwargs)
        
        should_calc = True

        if len(kwargs.get('update_fields', [])) > 0:
            should_calc = False
        
        if should_calc:
            self.calculate_rankings()

    def calculate_rankings(self):
        schedule = self.get_schedule()

        wins = [0, 0, 0, 0, 0, 0]
        losses = [0, 0, 0, 0, 0, 0]
        ties = [0, 0, 0, 0, 0, 0]
        total_points = [0, 0, 0, 0, 0, 0]

        for match_num in range(len(schedule)): # we need the match number (from 0) to be able to grab scores
            match = schedule[match_num] # get the players in the match as array
            
            red_score = self.get_red_score(match_num + 1)
            blue_score = self.get_blue_score(match_num + 1)

            if red_score == None or blue_score == None: # check if the match has happened yet
                continue

            for player_index in range(0, 3): # iterate through red alliance 
                player = match[player_index]
                
                if player == -1: # there is no player -1
                    continue

                total_points[player] += red_score
                
                if red_score > blue_score:
                    wins[player] += 1
                elif red_score < blue_score:
                    losses[player] += 1
                else:
                    ties[player] += 1
            
            for player_index in range(3, 6): # iterate through blue alliance 
                player = match[player_index]
                
                if player == -1: # there is no player -1
                    continue

                total_points[player] += blue_score
                
                if blue_score > red_score:
                    wins[player] += 1
                elif blue_score < red_score:
                    losses[player] += 1
                else:
                    ties[player] += 1
        
        player1_info = {'name': self.player1, 'wins':wins[0], 'losses':losses[0], 'ties':ties[0], 'total_points':total_points[0], 'absent':self.player1_absent}
        player2_info = {'name': self.player2, 'wins':wins[1], 'losses':losses[1], 'ties':ties[1], 'total_points':total_points[1], 'absent':self.player2_absent}
        player3_info = {'name': self.player3, 'wins':wins[2], 'losses':losses[2], 'ties':ties[2], 'total_points':total_points[2], 'absent':self.player3_absent}
        player4_info = {'name': self.player4, 'wins':wins[3], 'losses':losses[3], 'ties':ties[3], 'total_points':total_points[3], 'absent':self.player4_absent}
        player5_info = {'name': self.player5, 'wins':wins[4], 'losses':losses[4], 'ties':ties[4], 'total_points':total_points[4], 'absent':self.player5_absent}
        player6_info = {'name': self.player6, 'wins':wins[5], 'losses':losses[5], 'ties':ties[5], 'total_points':total_points[5], 'absent':self.player6_absent}

        info_list = [player1_info, player2_info, player3_info, player4_info, player5_info, player6_info]

        info_list = sorted(info_list, key = lambda x: (x['wins'], x['total_points']), reverse=True)

        self.rank1_info = info_list[0]
        self.rank2_info = info_list[1]
        self.rank3_info = info_list[2]
        self.rank4_info = info_list[3]
        self.rank5_info = info_list[4]
        self.rank6_info = info_list[5]


        self.save(update_fields=['rank1_info', 'rank2_info', 'rank3_info', 'rank4_info', 'rank5_info', 'rank6_info'])
        

    rank1_info = models.JSONField(null=True, blank=True)
    rank2_info = models.JSONField(null=True, blank=True)
    rank3_info = models.JSONField(null=True, blank=True)
    rank4_info = models.JSONField(null=True, blank=True)
    rank5_info = models.JSONField(null=True, blank=True)
    rank6_info = models.JSONField(null=True, blank=True)

    def get_player(self, num):
        if num == 1:
            return self.player1
        elif num == 2:
            return self.player2
        elif num == 3:
            return self.player3
        elif num == 4:
            return self.player4
        elif num == 5:
            return self.player5
        elif num == 6:
            return self.player6
        else:
            return ''

    def get_prepared_schedule(self):
        schedule = copy.deepcopy(self.get_schedule())
        
        for i in range(len(schedule)):
            for j in range(0, 6):
                print(schedule[i][j])
                schedule[i][j] = self.get_player(schedule[i][j] + 1)
            schedule[i].append(self.get_red_score(i + 1))
            schedule[i].append(self.get_blue_score(i + 1))
        
        return schedule
    
    def get_red_score(self, match):
        if match == 1:
            return self.match_1_red
        elif match == 2:
            return self.match_2_red
        elif match == 3:
            return self.match_3_red
        elif match == 4:
            return self.match_4_red
        elif match == 5:
            return self.match_5_red
        elif match == 6:
            return self.match_6_red
        elif match == 7:
            return self.match_7_red
        elif match == 8:
            return self.match_8_red
        elif match == 9:
            return self.match_9_red
        elif match == 10:
            return self.match_10_red
        elif match == 11:
            return self.match_11_red
        elif match == 12:
            return self.match_12_red
        elif match == 13:
            return self.match_13_red
        elif match == 14:
            return self.match_14_red
        elif match == 15:
            return self.match_15_red

    def get_blue_score(self, match):
        if match == 1:
            return self.match_1_blue
        elif match == 2:
            return self.match_2_blue
        elif match == 3:
            return self.match_3_blue
        elif match == 4:
            return self.match_4_blue
        elif match == 5:
            return self.match_5_blue
        elif match == 6:
            return self.match_6_blue
        elif match == 7:
            return self.match_7_blue
        elif match == 8:
            return self.match_8_blue
        elif match == 9:
            return self.match_9_blue
        elif match == 10:
            return self.match_10_blue
        elif match == 11:
            return self.match_11_blue
        elif match == 12:
            return self.match_12_blue
        elif match == 13:
            return self.match_13_blue
        elif match == 14:
            return self.match_14_blue
        elif match == 15:
            return self.match_15_blue
        



# Schedule uses players 0-5, with -1 as no player (filling the gap makes calculations easier)

SIX_PLAYER_SCHEDULE = [
    [0, 1, 2, 3, 4, 5],
    [0, 1, 3, 2, 4, 5],
    [0, 1, 4, 2, 3, 5],
    [0, 1, 5, 2, 3, 4],
    [0, 2, 3, 1, 4, 5],
    [0, 2, 4, 1, 3, 5],
    [0, 2, 5, 1, 3, 4],
    [0, 3, 4, 1, 2, 5],
    [0, 3, 5, 1, 2, 4],
    [0, 4, 5, 1, 2, 3]]

FIVE_PLAYER_SCHEDULE = [
    [0, 1, -1, 2, 3, -1],
    [0, 1, -1, 2, 4, -1],
    [0, 1, -1, 3, 4, -1],
    [0, 2, -1, 1, 3, -1],
    [0, 2, -1, 1, 4, -1],
    [0, 2, -1, 3, 4, -1],
    [0, 3, -1, 1, 2, -1],
    [0, 3, -1, 1, 4, -1],
    [0, 3, -1, 2, 4, -1],
    [0, 4, -1, 1, 2, -1],
    [0, 4, -1, 1, 3, -1],
    [0, 4, -1, 2, 3, -1],
    [1, 2, -1, 3, 4, -1],
    [1, 3, -1, 2, 4, -1],
    [1, 4, -1, 2, 3, -1]]

FOUR_PLAYER_SCHEDULE = [
    [0, 1, -1, 2, 3, -1],
    [0, 1, -1, 2, 3, -1],
    [0, 1, -1, 2, 3, -1],
    [0, 2, -1, 1, 3, -1],
    [0, 2, -1, 1, 3, -1],
    [0, 2, -1, 1, 3, -1],
    [0, 3, -1, 1, 2, -1],
    [0, 3, -1, 1, 2, -1],
    [0, 3, -1, 1, 2, -1]]