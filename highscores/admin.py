from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import CleanCodeSubmission, Leaderboard, Score, ExemptedIP

# Register your models here.


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('player', 'score', 'leaderboard', 'approved', 'time_set', 'ip', 'client_version', 'game_options_display')
    list_filter = ('approved', 'time_set', 'leaderboard', 'client_version')
    search_fields = ('player__username', 'leaderboard__name', 'ip', 'clean_code')
    raw_id_fields = ('player', 'leaderboard')
    readonly_fields = ('time_set', 'time_data', 'game_options_display')
    fieldsets = (
        ('Score Information', {
            'fields': ('player', 'score', 'leaderboard', 'approved')
        }),
        ('Technical Details', {
            'fields': ('clean_code', 'decrypted_code', 'client_version', 'time_of_score', 'robot_position', 'game_options_display', 'time_data')
        }),
        ('Submission Info', {
            'fields': ('source', 'ip', 'time_set')
        }),
    )
    list_per_page = 50
    date_hierarchy = 'time_set'
    actions = ['approve_scores', 'unapprove_scores']

    def game_options_display(self, obj):
        """Display the game options from decrypted code"""
        if not obj.decrypted_code:
            return "No decrypted code available"
        
        try:
            dataset = obj.decrypted_code.split(',')
            if len(dataset) >= 10:
                game_options = dataset[9].strip()
                return game_options
            else:
                return "Game options not found"
        except Exception as e:
            return f"Error parsing game options: {str(e)}"
    
    game_options_display.short_description = "Game Options"

    def approve_scores(self, request, queryset):
        queryset.update(approved=True)
    approve_scores.short_description = "Approve selected scores"

    def unapprove_scores(self, request, queryset):
        queryset.update(approved=False)
    unapprove_scores.short_description = "Unapprove selected scores"


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'game', 'game_slug', 'auto_or_teleop', 'robot', 'message')
    list_filter = ('game', 'auto_or_teleop')
    search_fields = ('name', 'robot', 'message')
    list_editable = ('message',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'robot', 'game', 'game_slug', 'auto_or_teleop')
        }),
        ('Additional Info', {
            'fields': ('message',)
        }),
    )


@admin.register(CleanCodeSubmission)
class CleanCodeSubmissionAdmin(admin.ModelAdmin):
    list_display = ('player', 'score', 'leaderboard', 'time_set', 'ip')
    list_filter = ('time_set', 'leaderboard')
    search_fields = ('player__username', 'leaderboard__name', 'clean_code', 'ip')
    raw_id_fields = ('player', 'leaderboard')
    readonly_fields = ('time_set',)
    date_hierarchy = 'time_set'


@admin.register(ExemptedIP)
class ExemptedIPAdmin(admin.ModelAdmin):
    list_display = ('ip', 'reason')
    search_fields = ('ip', 'reason')
    list_editable = ('reason',)


admin.site.site_header = "Second Robotics Admin Panel"
