from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import TaskViewSet, TaskBoardView, TaskFilterOptionsView, TaskAssigneeCountsView, TeamViewSet, SprintViewSet, BacklogView

team_router = SimpleRouter()
team_router.register(r'teams', TeamViewSet, basename='team')

task_router = SimpleRouter()
task_router.register(r'', TaskViewSet, basename='task')

sprint_router = SimpleRouter()
sprint_router.register(r'sprints', SprintViewSet, basename='sprint')

urlpatterns = [
    path('board/', TaskBoardView.as_view(), name='task-board'),
    path('backlog/', BacklogView.as_view(), name='task-backlog'),
    path('filters/', TaskFilterOptionsView.as_view(), name='task-filters'),
    path('assignee-counts/', TaskAssigneeCountsView.as_view(), name='task-assignee-counts'),
    path('', include(team_router.urls)),
    path('', include(sprint_router.urls)),
    path('', include(task_router.urls)),
]
