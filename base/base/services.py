from django.db import models, transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.http import HttpRequest
from typing import List, Dict, Any, Optional
import json

from .models import ArchiveLog, ArchiveConfiguration


class ArchiveService:
    """
    Сервис для управления архивированием записей
    """
    
    @classmethod
    def archive_record(
        cls, 
        instance, 
        user=None, 
        reason="", 
        request=None,
        cascade=True
    ) -> bool:
        """
        Архивирует запись и связанные с ней записи
        
        Args:
            instance: Экземпляр модели для архивирования
            user: Пользователь, выполняющий архивирование
            reason: Причина архивирования
            request: HTTP запрос для получения дополнительной информации
            cascade: Выполнять каскадное архивирование
        """
        if not hasattr(instance, 'is_archived'):
            raise ValidationError("Модель не поддерживает архивирование")
        
        if instance.is_archived:
            raise ValidationError("Запись уже архивирована")
        
        # Проверяем права доступа
        config = ArchiveConfiguration.get_config(instance.__class__)
        if config.archive_permission and user:
            if not user.has_perm(config.archive_permission):
                raise PermissionDenied("Нет прав на архивирование")
        
        # Проверяем обязательность причины
        if config.require_reason and not reason.strip():
            raise ValidationError("Необходимо указать причину архивирования")
        
        with transaction.atomic():
            # Архивируем основную запись
            instance.archive(user, reason)
            
            # Архивируем связанные записи если включено каскадное архивирование
            if cascade and config.cascade_archive:
                cls._archive_related_records(instance, user, reason, request)
            
            # Логируем действие
            cls._log_archive_action(instance, user, 'archive', reason, request)
            
        return True
    
    @classmethod
    def restore_record(
        cls, 
        instance, 
        user=None, 
        request=None,
        cascade=True
    ) -> bool:
        """
        Восстанавливает запись из архива
        
        Args:
            instance: Экземпляр модели для восстановления
            user: Пользователь, выполняющий восстановление
            request: HTTP запрос для получения дополнительной информации
            cascade: Выполнять каскадное восстановление
        """
        if not hasattr(instance, 'is_archived'):
            raise ValidationError("Модель не поддерживает архивирование")
        
        if not instance.is_archived:
            raise ValidationError("Запись не архивирована")
        
        # Проверяем права доступа
        config = ArchiveConfiguration.get_config(instance.__class__)
        if not config.allow_restore:
            raise ValidationError("Восстановление не разрешено для данной модели")
        
        if config.restore_permission and user:
            if not user.has_perm(config.restore_permission):
                raise PermissionDenied("Нет прав на восстановление")
        
        with transaction.atomic():
            # Восстанавливаем основную запись
            instance.restore(user)
            
            # Восстанавливаем связанные записи если включено каскадное восстановление
            if cascade and config.cascade_restore:
                cls._restore_related_records(instance, user, request)
            
            # Логируем действие
            cls._log_archive_action(instance, user, 'restore', "", request)
            
        return True
    
    @classmethod
    def bulk_archive(
        cls, 
        queryset, 
        user=None, 
        reason="", 
        request=None
    ) -> int:
        """
        Массовое архивирование записей
        
        Args:
            queryset: QuerySet записей для архивирования
            user: Пользователь, выполняющий архивирование
            reason: Причина архивирования
            request: HTTP запрос для получения дополнительной информации
            
        Returns:
            Количество архивированных записей
        """
        archived_count = 0
        
        with transaction.atomic():
            for instance in queryset:
                try:
                    cls.archive_record(instance, user, reason, request)
                    archived_count += 1
                except (ValidationError, PermissionDenied) as e:
                    # Логируем ошибку но продолжаем обработку
                    print(f"Ошибка архивирования {instance}: {e}")
                    continue
        
        return archived_count
    
    @classmethod
    def bulk_restore(
        cls, 
        queryset, 
        user=None, 
        request=None
    ) -> int:
        """
        Массовое восстановление записей
        
        Args:
            queryset: QuerySet архивированных записей для восстановления
            user: Пользователь, выполняющий восстановление
            request: HTTP запрос для получения дополнительной информации
            
        Returns:
            Количество восстановленных записей
        """
        restored_count = 0
        
        with transaction.atomic():
            for instance in queryset:
                try:
                    cls.restore_record(instance, user, request)
                    restored_count += 1
                except (ValidationError, PermissionDenied) as e:
                    # Логируем ошибку но продолжаем обработку
                    print(f"Ошибка восстановления {instance}: {e}")
                    continue
        
        return restored_count
    
    @classmethod
    def _archive_related_records(cls, instance, user, reason, request):
        """
        Архивирует связанные записи
        """
        # Получаем все связанные поля
        related_fields = cls._get_related_fields(instance)
        
        for field_name, field in related_fields.items():
            # Получаем связанные записи
            if field.many_to_many:
                related_objects = getattr(instance, field_name).all()
            else:
                related_obj = getattr(instance, field_name)
                related_objects = [related_obj] if related_obj is not None else []
            
            # Архивируем связанные записи
            for related_obj in related_objects:
                if related_obj and hasattr(related_obj, 'is_archived') and not related_obj.is_archived:
                    try:
                        cls.archive_record(related_obj, user, f"Каскадное архивирование: {reason}", request, cascade=False)
                    except Exception as e:
                        print(f"Ошибка каскадного архивирования {related_obj}: {e}")
    
    @classmethod
    def _restore_related_records(cls, instance, user, request):
        """
        Восстанавливает связанные записи
        """
        # Получаем все связанные поля
        related_fields = cls._get_related_fields(instance)
        
        for field_name, field in related_fields.items():
            # Получаем связанные записи
            if field.many_to_many:
                related_objects = getattr(instance, field_name).all()
            else:
                related_obj = getattr(instance, field_name)
                related_objects = [related_obj] if related_obj is not None else []
            
            # Восстанавливаем связанные записи
            for related_obj in related_objects:
                if related_obj and hasattr(related_obj, 'is_archived') and related_obj.is_archived:
                    try:
                        cls.restore_record(related_obj, user, request, cascade=False)
                    except Exception as e:
                        print(f"Ошибка каскадного восстановления {related_obj}: {e}")
    
    @classmethod
    def _get_related_fields(cls, instance):
        """
        Получает все связанные поля модели, которые поддерживают архивирование
        """
        related_fields = {}
        
        for field in instance._meta.get_fields():
            if field.is_relation:
                # Проверяем, поддерживает ли связанная модель архивирование
                if hasattr(field, 'related_model') and field.related_model:
                    if hasattr(field.related_model, 'is_archived'):
                        related_fields[field.name] = field
        
        return related_fields
    
    @classmethod
    def _log_archive_action(cls, instance, user, action, reason, request):
        """
        Логирует действие архивирования
        """
        try:
            # Получаем данные запроса
            ip_address = None
            user_agent = ""
            
            if request and isinstance(request, HttpRequest):
                ip_address = cls._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Создаем лог
            ArchiveLog.objects.create(
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.pk,
                action=action,
                user=user,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                previous_data=cls._get_instance_data(instance) if action == 'archive' else None,
                new_data=cls._get_instance_data(instance) if action == 'restore' else None,
            )
        except Exception as e:
            print(f"Ошибка логирования архивирования: {e}")
    
    @classmethod
    def _get_client_ip(cls, request):
        """
        Получает IP адрес клиента
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def _get_instance_data(cls, instance):
        """
        Получает данные экземпляра для логирования
        """
        try:
            data = {}
            for field in instance._meta.fields:
                if field.name not in ['password', 'secret_key']:  # Исключаем чувствительные поля
                    value = getattr(instance, field.name)
                    if hasattr(value, 'isoformat'):  # Для datetime полей
                        value = value.isoformat()
                    data[field.name] = value
            return data
        except Exception:
            return None


class ArchiveQuerySet(models.QuerySet):
    """
    QuerySet с поддержкой архивирования
    """
    
    def active(self):
        """
        Возвращает только активные (неархивированные) записи
        """
        return self.filter(is_archived=False)
    
    def archived(self):
        """
        Возвращает только архивированные записи
        """
        return self.filter(is_archived=True)
    
    def archive_by_reason(self, reason):
        """
        Возвращает записи, архивированные по определенной причине
        """
        return self.filter(is_archived=True, archive_reason__icontains=reason)
    
    def archive_by_user(self, user):
        """
        Возвращает записи, архивированные определенным пользователем
        """
        return self.filter(is_archived=True, archived_by=user)
    
    def archive_since(self, date):
        """
        Возвращает записи, архивированные после указанной даты
        """
        return self.filter(is_archived=True, archived_at__gte=date)
    
    def archive_before(self, date):
        """
        Возвращает записи, архивированные до указанной даты
        """
        return self.filter(is_archived=True, archived_at__lte=date)


class ArchiveManager(models.Manager):
    """
    Менеджер с поддержкой архивирования
    """
    
    def get_queryset(self):
        return ArchiveQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def archived(self):
        return self.get_queryset().archived()
    
    def archive_record(self, instance, user=None, reason="", request=None):
        return ArchiveService.archive_record(instance, user, reason, request)
    
    def restore_record(self, instance, user=None, request=None):
        return ArchiveService.restore_record(instance, user, request)
    
    def bulk_archive(self, queryset, user=None, reason="", request=None):
        return ArchiveService.bulk_archive(queryset, user, reason, request)
    
    def bulk_restore(self, queryset, user=None, request=None):
        return ArchiveService.bulk_restore(queryset, user, request)
