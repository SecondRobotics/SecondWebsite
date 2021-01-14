from django import forms

class SubmitScore(forms.Form):
    name = forms.CharField(label="Name", max_length=30)
    check = forms.BooleanField(label="I didn't cheat LMAO")