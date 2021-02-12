from django.contrib import admin
from .models import *

# Register your models here.

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('player_name', 'event',)
    list_filter = ('event',)
    search_fields = ('player_name',)

admin.site.register(Event)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Ranking)
admin.site.register(Match)
admin.site.register(ElimsAlliance)
admin.site.register(ChampionshipPoints)
