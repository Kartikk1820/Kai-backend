from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import TaskViewSet, TaskBoardView, TaskFilterOptionsView, TeamViewSet

team_router = SimpleRouter()
team_router.register(r'teams', TeamViewSet, basename='team')

task_router = SimpleRouter()
task_router.register(r'', TaskViewSet, basename='task')

urlpatterns = [
    path('board/', TaskBoardView.as_view(), name='task-board'),
    path('filters/', TaskFilterOptionsView.as_view(), name='task-filters'),
    path('', include(team_router.urls)),
    path('', include(task_router.urls)),
]
