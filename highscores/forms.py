from typing import Type
from django import forms
from . import models


class ScoreForm(forms.Form):
    leaderboard = None
    score = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Score"}),
    )
    source = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Url to image or video"}
        ),
    )
    clean_code = forms.CharField(
        max_length=600,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Clean code (automatically copied to your clipboard after the match)",
            }
        ),
    )


def get_score_form(game_slug: str) -> Type[ScoreForm]:
    class GameScoreForm(ScoreForm):
        leaderboard = forms.ModelChoiceField(
            required=True,
            queryset=models.Leaderboard.objects.filter(game_slug=game_slug),
            widget=forms.Select(attrs={"class": "form-control"}),
        )
    return GameScoreForm
