from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import redirect
from django.core.management import call_command
from .models import User

class CustomUserAdmin(UserAdmin):
    change_list_template = "admin/users/user/change_list.html"

    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'role', 'sub_position', 'manager')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'role'),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('seed-users/', self.admin_site.admin_view(self.seed_users_view), name='seed-users'),
        ]
        return custom_urls + urls

    def seed_users_view(self, request):
        try:
            call_command('seed_users')
            self.message_user(request, "Dummy users have been seeded successfully!", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error seeding users: {str(e)}", level=messages.ERROR)
        
        return redirect('..')

admin.site.register(User, CustomUserAdmin)
