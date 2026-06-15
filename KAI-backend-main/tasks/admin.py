from django.contrib import admin
from .models import Task, Team, Comment, Attachment, TaskLink, TaskKeyCounter

admin.site.register([Team, Comment, Attachment, TaskLink, TaskKeyCounter])


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('key', 'title', 'status', 'priority', 'assignee', 'team')
    list_filter = ('status', 'priority')
    search_fields = ('key', 'title')
