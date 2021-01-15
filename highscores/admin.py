from django.contrib import admin
from .models import Leaderboard, Score

# Register your models here.

admin.site.register(Leaderboard)
admin.site.register(Score)