from django.contrib import admin
from .models import HistoricEvent, Staff

# Register your models here.


class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'email')
    search_fields = ('name',)


class HistoricEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'first_place', 'second_place')
    search_fields = ('name',)


admin.site.register(Staff, StaffAdmin)
admin.site.register(HistoricEvent, HistoricEventAdmin)
