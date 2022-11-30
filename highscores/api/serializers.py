from rest_framework.serializers import ModelSerializer
from discordoauth2.models import User
from ..models import Score, Leaderboard


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'display_name', 'username',
                  'avatar', 'date_joined', 'is_staff']


# ScoreSerializer contains the fields leaderboard, player (display name and avatar), and score.
class ScoreSerializer(ModelSerializer):
    player = UserSerializer()

    class Meta:
        model = Score
        fields = ['leaderboard', 'player', 'score']


class LeaderboardSerializer(ModelSerializer):
    class Meta:
        model = Leaderboard
        fields = '__all__'
