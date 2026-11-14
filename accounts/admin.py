from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin for MedStep users, including role, contact number and photo."""

    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'is_active', 'last_login',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'contact_number')
    ordering = ('last_name', 'first_name')

    # Edit page: Django's default sections + a MedStep section.
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('MedStep', {'fields': ('role', 'contact_number', 'profile_photo')}),
    )

    # "Add user" page: lets a lab admin create instructor accounts directly.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name', 'role',
                'usable_password', 'password1', 'password2',
            ),
        }),
    )
