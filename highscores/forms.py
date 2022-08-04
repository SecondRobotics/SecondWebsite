from django import forms
from . import models


class ScoreForm(forms.Form):
    leaderboard = None
    score = forms.IntegerField(required=True)
    source = forms.CharField(required=True)
    clean_code = forms.CharField(max_length=600, required=True)


class IRScoreForm(ScoreForm):
    leaderboard = forms.ModelChoiceField(required=True,
                                         queryset=models.Leaderboard.objects.filter(
                                             game='Infinite Recharge'),
                                         )


class RRScoreForm(ScoreForm):
    leaderboard = forms.ModelChoiceField(required=True,
                                         queryset=models.Leaderboard.objects.filter(
                                             game='Rapid React'),
                                         )


class FFScoreForm(ScoreForm):
    leaderboard = forms.ModelChoiceField(required=True,
                                         queryset=models.Leaderboard.objects.filter(
                                             game='Freight Frenzy'),
                                         )


class TPScoreForm(ScoreForm):
    leaderboard = forms.ModelChoiceField(required=True,
                                         queryset=models.Leaderboard.objects.filter(
                                             game='Tipping Point'),
                                         )


class SUScoreForm(ScoreForm):
    leaderboard = forms.ModelChoiceField(required=True,
                                         queryset=models.Leaderboard.objects.filter(
                                             game='Spin Up'),
                                         )
