from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            'Additional Information',
            {
                'fields': (
                    'user_type',
                    'is_email_verified',
                )
            }
        )
    )
    list_display = ('username', 'email', 'user_type', 'is_email_verified', 'is_staff')
    list_filter = ('user_type', 'is_email_verified', 'is_staff', 'is_active')
    search_fields = ('username', 'email')

admin.site.register(User, CustomUserAdmin)