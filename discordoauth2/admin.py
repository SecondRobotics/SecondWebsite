from django.contrib import admin
from .models import User

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    exclude = ('password', 'first_name', 'last_name')

    list_display = ('username', 'display_name', 'email', 'is_staff', 'is_active',
                    'last_login', 'date_joined', 'id',)
    list_filter = ('is_staff', 'is_superuser', 'is_active',
                   'last_login', 'date_joined',)
    search_fields = ('username', 'display_name', 'email', 'id',)


admin.site.register(User, UserAdmin)
