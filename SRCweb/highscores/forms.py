from django import forms
from django.forms import widgets
from . import models
from django.forms import ModelForm
from django import forms

class ScoreForm(ModelForm):
    class Meta:
        model = models.Score
        fields = ('leaderboard', 'player_name', 'score')
    # widgets = {
    #     "leaderboard": forms.Select(attrs={'class': 'form-control'}),
    #     "player_name": forms.TextInput(attrs={'class': 'form-control'}),
    #     "score": forms.NumberInput(attrs={'class': 'form-control'}),
    # }