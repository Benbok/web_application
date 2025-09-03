from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_viewsets import (
    ArchiveLogViewSet, ArchiveConfigurationViewSet, ArchiveActionViewSet
)

# Создаем роутер для API
router = DefaultRouter()
router.register(r'archive-logs', ArchiveLogViewSet, basename='archive-logs')
router.register(r'archive-configurations', ArchiveConfigurationViewSet, basename='archive-configurations')
router.register(r'archive-actions', ArchiveActionViewSet, basename='archive-actions')

# URL-паттерны для API
urlpatterns = [
    # Основные эндпоинты API
    path('api/v1/', include(router.urls)),
    
    # Дополнительные эндпоинты для действий архивирования
    path('api/v1/archive/record/', ArchiveActionViewSet.as_view({
        'post': 'archive_record'
    }), name='api-archive-record'),
    
    path('api/v1/archive/restore/', ArchiveActionViewSet.as_view({
        'post': 'restore_record'
    }), name='api-restore-record'),
    
    path('api/v1/archive/bulk/', ArchiveActionViewSet.as_view({
        'post': 'bulk_archive'
    }), name='api-bulk-archive'),
    
    path('api/v1/archive/status/', ArchiveActionViewSet.as_view({
        'get': 'get_archive_status'
    }), name='api-archive-status'),
    
    # Статистика архивирования
    path('api/v1/archive/statistics/', ArchiveLogViewSet.as_view({
        'get': 'statistics'
    }), name='api-archive-statistics'),
    
    # Сброс конфигурации
    path('api/v1/archive-configurations/<int:pk>/reset/', 
         ArchiveConfigurationViewSet.as_view({
             'post': 'reset_to_defaults'
         }), name='api-reset-configuration'),
]

# Добавляем поддержку авторизации DRF
urlpatterns += [
    path('api-auth/', include('rest_framework.urls')),
]
