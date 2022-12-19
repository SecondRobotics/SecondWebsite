from rest_framework.serializers import ModelSerializer
from discordoauth2.models import User
from ..models import Score, Leaderboard


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'display_name', 'username',
                  'avatar', 'date_joined', 'is_staff']


class LeaderboardSerializer(ModelSerializer):
    class Meta:
        model = Leaderboard
        fields = '__all__'


class ScoreWithLeaderboardSerializer(ModelSerializer):
    leaderboard = LeaderboardSerializer()

    class Meta:
        model = Score
        fields = ['leaderboard', 'score', 'time_set']


class ScoreWithPlayerSerializer(ModelSerializer):
    player = UserSerializer()

    class Meta:
        model = Score
        fields = ['player', 'score', 'time_set']
