from django.contrib import admin
from .models import *

# Register your models here.

class DivisionAdmin(admin.ModelAdmin):
    list_display = ('week', 'level')
    list_filter = ('week', 'level')
    search_fields = ('week', 'level')
    exclude = ('rank1_info', 'rank2_info', 'rank3_info', 'rank4_info', 'rank5_info', 'rank6_info')

admin.site.register(Division, DivisionAdmin)