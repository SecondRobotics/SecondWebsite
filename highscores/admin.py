from django.contrib import admin
from .models import Leaderboard, Score

# Register your models here.

class ScoreAdmin(admin.ModelAdmin):
    list_display = ('player_name', 'score', 'leaderboard', 'approved',)
    list_filter = ('approved', 'time_set', 'leaderboard')
    #readonly_fields = ('source',)
    search_fields = ('player_name',)

admin.site.site_header = "Second Robotics Admin Panel"
admin.site.register(Leaderboard)
admin.site.register(Score, ScoreAdmin)