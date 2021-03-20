from django.contrib import admin
from .models import *

# Register your models here.

class MatchupAdmin(admin.ModelAdmin):
    list_display = ('red_alliance', 'blue_alliance', 'winner', 'week')
    list_filter = ('red_alliance', 'blue_alliance')
    search_fields = ('red_alliance__name', 'blue_alliance__name')

admin.site.register(Alliance)
admin.site.register(Matchup, MatchupAdmin)