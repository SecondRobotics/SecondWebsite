from django.contrib import admin
from .models import Leaderboard, Score

# Register your models here.

class ScoreAdmin(admin.ModelAdmin):
    list_display = ('player', 'score', 'leaderboard', 'approved',)
    list_filter = ('approved', 'time_set', 'leaderboard')
    search_fields = ('player',)

admin.site.site_header = "Second Robotics Admin Panel"
admin.site.register(Leaderboard)
admin.site.register(Score, ScoreAdmin)