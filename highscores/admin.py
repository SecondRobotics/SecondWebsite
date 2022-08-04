from django.contrib import admin
from .models import CleanCodeSubmission, Leaderboard, Score

# Register your models here.


class ScoreAdmin(admin.ModelAdmin):
    list_display = ('player', 'score', 'leaderboard', 'approved',)
    list_filter = ('approved', 'time_set', 'leaderboard')
    search_fields = ('player',)


class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'game', 'game_slug', 'auto_or_teleop',)
    list_filter = ('game', 'game', 'auto_or_teleop',)
    search_fields = ('name',)


admin.site.site_header = "Second Robotics Admin Panel"
admin.site.register(Leaderboard, LeaderboardAdmin)
admin.site.register(Score, ScoreAdmin)
admin.site.register(CleanCodeSubmission)
