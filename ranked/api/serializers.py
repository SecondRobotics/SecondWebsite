from rest_framework import serializers
from ranked.models import GameMode, Match, PlayerElo, EloHistory

class GameModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameMode
        fields = '__all__'

class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = '__all__'

class PlayerEloSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerElo
        fields = '__all__'

class EloHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EloHistory
        fields = '__all__'

class LeaderboardSerializer(serializers.Serializer):
    player_id = serializers.IntegerField()
    rank_number = serializers.FloatField()
    rank_name = serializers.CharField()
