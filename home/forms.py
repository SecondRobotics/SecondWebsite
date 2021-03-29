from discordoauth2.models import User
from django.forms import ModelForm

class ProfileForm(ModelForm):
    class Meta:
        model = User
        fields = ('display_name',)