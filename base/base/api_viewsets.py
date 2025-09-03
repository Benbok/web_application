from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from typing import List, Dict, Any

from .models import ArchiveLog, ArchiveConfiguration
from .api_serializers import (
    ArchiveLogSerializer, ArchiveConfigurationSerializer,
    ArchiveActionSerializer, ArchiveStatusSerializer,
    BulkArchiveResponseSerializer, ArchiveFilterSerializer
)
from .services import ArchiveService


class ArchiveLogPagination(PageNumberPagination):
    """
    Пагинация для логов архивирования
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ArchiveLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра логов архивирования
    """
    queryset = ArchiveLog.objects.all()
    serializer_class = ArchiveLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ArchiveLogPagination
    
    def get_queryset(self):
        """
        Фильтрация логов по параметрам запроса
        """
        queryset = ArchiveLog.objects.all()
        
        # Фильтр по действию
        action_filter = self.request.query_params.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        # Фильтр по пользователю
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Фильтр по модели
        model_name = self.request.query_params.get('model')
        if model_name:
            queryset = queryset.filter(content_type__model=model_name)
        
        # Фильтр по приложению
        app_label = self.request.query_params.get('app')
        if app_label:
            queryset = queryset.filter(content_type__app_label=app_label)
        
        # Фильтр по дате
        since_date = self.request.query_params.get('since')
        if since_date:
            queryset = queryset.filter(timestamp__gte=since_date)
        
        until_date = self.request.query_params.get('until')
        if until_date:
            queryset = queryset.filter(timestamp__lte=until_date)
        
        return queryset.select_related('content_type', 'user').order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Получение статистики архивирования
        """
        total_logs = ArchiveLog.objects.count()
        archive_count = ArchiveLog.objects.filter(action='archive').count()
        restore_count = ArchiveLog.objects.filter(action='restore').count()
        
        # Статистика по моделям
        model_stats = ArchiveLog.objects.values(
            'content_type__app_label', 'content_type__model'
        ).annotate(
            archive_count=Q(action='archive').count(),
            restore_count=Q(action='restore').count()
        )
        
        # Статистика по пользователям
        user_stats = ArchiveLog.objects.values(
            'user__username', 'user__first_name', 'user__last_name'
        ).annotate(
            total_actions=Q().count()
        ).order_by('-total_actions')[:10]
        
        return Response({
            'total_logs': total_logs,
            'archive_count': archive_count,
            'restore_count': restore_count,
            'model_statistics': list(model_stats),
            'top_users': list(user_stats)
        })


class ArchiveConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления конфигурацией архивирования
    """
    queryset = ArchiveConfiguration.objects.all()
    serializer_class = ArchiveConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_queryset(self):
        """
        Фильтрация конфигураций
        """
        queryset = ArchiveConfiguration.objects.all()
        
        # Фильтр по приложению
        app_label = self.request.query_params.get('app')
        if app_label:
            queryset = queryset.filter(content_type__app_label=app_label)
        
        # Фильтр по модели
        model_name = self.request.query_params.get('model')
        if model_name:
            queryset = queryset.filter(content_type__model=model_name)
        
        return queryset.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model'
        )
    
    @action(detail=True, methods=['post'])
    def reset_to_defaults(self, request, pk=None):
        """
        Сброс конфигурации к значениям по умолчанию
        """
        config = self.get_object()
        
        # Сбрасываем к значениям по умолчанию
        config.is_archivable = True
        config.cascade_archive = True
        config.cascade_restore = True
        config.auto_archive_related = True
        config.archive_after_days = None
        config.show_archived_in_list = True
        config.show_archived_in_search = False
        config.allow_restore = True
        config.require_reason = True
        config.archive_permission = None
        config.restore_permission = None
        config.save()
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


class ArchiveActionViewSet(viewsets.ViewSet):
    """
    ViewSet для выполнения действий архивирования
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def archive_record(self, request):
        """
        Архивирование одной записи
        """
        serializer = ArchiveActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        app_label = request.data.get('app_label')
        model_name = request.data.get('model_name')
        pk = request.data.get('pk')
        
        if not all([app_label, model_name, pk]):
            return Response(
                {'error': 'Необходимо указать app_label, model_name и pk'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Получаем модель и запись
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            model_class = content_type.model_class()
            instance = get_object_or_404(model_class, pk=pk)
            
            # Проверяем поддержку архивирования
            if not hasattr(instance, 'is_archived'):
                return Response(
                    {'error': 'Данная модель не поддерживает архивирование'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Архивируем запись
            success = ArchiveService.archive_record(
                instance=instance,
                user=request.user,
                reason=data.get('reason', ''),
                request=request,
                cascade=data.get('cascade', True)
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Запись успешно архивирована',
                    'record_id': pk,
                    'archived_at': timezone.now()
                })
            else:
                return Response(
                    {'error': 'Не удалось архивировать запись'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except (ContentType.DoesNotExist, ValidationError, PermissionDenied) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def restore_record(self, request):
        """
        Восстановление одной записи
        """
        serializer = ArchiveActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        app_label = request.data.get('app_label')
        model_name = request.data.get('model_name')
        pk = request.data.get('pk')
        
        if not all([app_label, model_name, pk]):
            return Response(
                {'error': 'Необходимо указать app_label, model_name и pk'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Получаем модель и запись
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            model_class = content_type.model_class()
            instance = get_object_or_404(model_class, pk=pk)
            
            # Проверяем поддержку архивирования
            if not hasattr(instance, 'is_archived'):
                return Response(
                    {'error': 'Данная модель не поддерживает архивирование'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Восстанавливаем запись
            success = ArchiveService.restore_record(
                instance=instance,
                user=request.user,
                request=request,
                cascade=data.get('cascade', True)
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Запись успешно восстановлена',
                    'record_id': pk,
                    'restored_at': timezone.now()
                })
            else:
                return Response(
                    {'error': 'Не удалось восстановить запись'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except (ContentType.DoesNotExist, ValidationError, PermissionDenied) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_archive(self, request):
        """
        Массовое архивирование записей
        """
        serializer = ArchiveActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        app_label = request.data.get('app_label')
        model_name = request.data.get('model_name')
        record_ids = data.get('record_ids', [])
        
        if not all([app_label, model_name, record_ids]):
            return Response(
                {'error': 'Необходимо указать app_label, model_name и record_ids'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Получаем модель
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            model_class = content_type.model_class()
            
            # Получаем QuerySet записей
            queryset = model_class.objects.filter(pk__in=record_ids)
            
            # Архивируем записи
            archived_count = ArchiveService.bulk_archive(
                queryset=queryset,
                user=request.user,
                reason=data.get('reason', ''),
                request=request
            )
            
            return Response({
                'success': True,
                'archived_count': archived_count,
                'total_requested': len(record_ids),
                'message': f'Успешно архивировано {archived_count} из {len(record_ids)} записей'
            })
            
        except (ContentType.DoesNotExist, ValidationError, PermissionDenied) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def get_archive_status(self, request):
        """
        Получение статуса архивирования записи
        """
        app_label = request.query_params.get('app_label')
        model_name = request.query_params.get('model_name')
        pk = request.query_params.get('pk')
        
        if not all([app_label, model_name, pk]):
            return Response(
                {'error': 'Необходимо указать app_label, model_name и pk'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Получаем модель и запись
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            model_class = content_type.model_class()
            instance = get_object_or_404(model_class, pk=pk)
            
            # Проверяем поддержку архивирования
            if not hasattr(instance, 'is_archived'):
                return Response(
                    {'error': 'Данная модель не поддерживает архивирование'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Создаем сериализатор для статуса
            status_data = {
                'is_archived': instance.is_archived,
                'archived_at': instance.archived_at,
                'archived_by': instance.archived_by,
                'archive_reason': instance.archive_reason
            }
            
            serializer = ArchiveStatusSerializer(data=status_data)
            serializer.is_valid()
            
            return Response(serializer.data)
            
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Модель не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
