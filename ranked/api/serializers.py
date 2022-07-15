from rest_framework.serializers import ModelSerializer
from ranked.models import GameMode, Match, PlayerElo, EloHistory


class GameModeSerializer(ModelSerializer):
    class Meta:
        model = GameMode
        fields = '__all__'


class MatchSerializer(ModelSerializer):
    class Meta:
        model = Match
        fields = '__all__'


class PlayerEloSerializer(ModelSerializer):
    class Meta:
        model = PlayerElo
        fields = '__all__'


class EloHistorySerializer(ModelSerializer):
    class Meta:
        model = EloHistory
        fields = '__all__'
