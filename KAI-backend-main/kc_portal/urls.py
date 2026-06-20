from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView,
)
from bids.views import GoogleSheetsWebhookView

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Webhooks
    path('api/webhooks/google-sheets/', GoogleSheetsWebhookView.as_view(), name='google-sheets-webhook'),

    # Auth + admin users/roles
    path('auth/', include('users.urls')),

    # Modules
    path('api/tasks/', include('tasks.urls')),
    path('api/hrms/', include('hrms.urls')),
    path('api/bids/', include('bids.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/documents/', include('documents.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
