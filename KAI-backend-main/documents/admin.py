from django.contrib import admin
from .models import SharedDocument, DocumentRequest

admin.site.register(SharedDocument)
admin.site.register(DocumentRequest)
