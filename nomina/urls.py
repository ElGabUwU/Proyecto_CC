"""
URL configuration for nomina project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),  # Carga todas las URLs de myapp desde '/'
]

# Servir archivos media en desarrollo (solo si no está usando S3)
if settings.DEBUG and (not hasattr(settings, 'AWS_ACCESS_KEY_ID') or not settings.AWS_ACCESS_KEY_ID):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)