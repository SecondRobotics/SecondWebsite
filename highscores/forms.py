from typing import Type
from django import forms
from . import models


class ScoreForm(forms.Form):
    leaderboard = None
    score = forms.IntegerField(required=True)
    source = forms.CharField(required=True)
    clean_code = forms.CharField(max_length=600, required=True)


def get_score_form(game_slug: str) -> Type[ScoreForm]:
    class GameScoreForm(ScoreForm):
        leaderboard = forms.ModelChoiceField(required=True,
                                             queryset=models.Leaderboard.objects.filter(
                                                 game_slug=game_slug),
                                             )
    return GameScoreForm
