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
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'user_type', 'manager')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'user_type'),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('seed-all/', self.admin_site.admin_view(self.seed_all_view), name='seed-all'),
        ]
        return custom_urls + urls

    def seed_all_view(self, request):
        try:
            call_command('seed_all')
            self.message_user(request, "Full data seed complete — users, teams, clients, bids, tasks & attendance created!", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Seed error: {str(e)}", level=messages.ERROR)
        return redirect('..')


admin.site.register(User, CustomUserAdmin)
