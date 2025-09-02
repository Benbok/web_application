from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class TimeStampedModel(models.Model):
    """
    Абстрактная базовая модель для автоматического отслеживания времени создания и обновления
    """
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        abstract = True


class ArchivableModel(models.Model):
    """
    Абстрактная базовая модель для поддержки архивирования записей
    """
    is_archived = models.BooleanField("Архивировано", default=False)
    archived_at = models.DateTimeField("Дата архивирования", null=True, blank=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Архивировано пользователем",
        related_name="%(class)s_archived"
    )
    archive_reason = models.TextField("Причина архивирования", blank=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['is_archived']),
            models.Index(fields=['archived_at']),
        ]

    def archive(self, user=None, reason=""):
        """
        Архивирует запись и все связанные с ней записи
        """
        if self.is_archived:
            raise ValidationError("Запись уже архивирована")
        
        # Архивируем текущую запись
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = user
        self.archive_reason = reason
        self.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'archive_reason'])
        
        # Архивируем связанные записи
        self._archive_related_records(user, reason)
        
        return True

    def restore(self, user=None):
        """
        Восстанавливает запись из архива
        """
        if not self.is_archived:
            raise ValidationError("Запись не архивирована")
        
        # Восстанавливаем текущую запись
        self.is_archived = False
        self.archived_at = None
        self.archived_by = None
        self.archive_reason = ""
        self.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'archive_reason'])
        
        # Восстанавливаем связанные записи
        self._restore_related_records(user)
        
        return True

    def _archive_related_records(self, user, reason):
        """
        Архивирует связанные записи (переопределяется в наследниках)
        """
        pass

    def _restore_related_records(self, user):
        """
        Восстанавливает связанные записи (переопределяется в наследниках)
        """
        pass

    def get_archive_status_display(self):
        """
        Возвращает человекочитаемый статус архивирования
        """
        if self.is_archived:
            return f"Архивировано {self.archived_at.strftime('%d.%m.%Y %H:%M')}"
        return "Активно"


class NotArchivedManager(models.Manager):
    """
    Менеджер для получения только неархивированных записей
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_archived=False)


class ArchivedManager(models.Manager):
    """
    Менеджер для получения только архивированных записей
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_archived=True)


class AllRecordsManager(models.Manager):
    """
    Менеджер для получения всех записей (архивированных и неархивированных)
    """
    def get_queryset(self):
        return super().get_queryset()


class ArchiveLog(models.Model):
    """
    Лог архивирования для аудита
    """
    ACTION_CHOICES = [
        ('archive', 'Архивирование'),
        ('restore', 'Восстановление'),
        ('delete', 'Удаление'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    action = models.CharField("Действие", max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    timestamp = models.DateTimeField("Время действия", auto_now_add=True)
    reason = models.TextField("Причина", blank=True)
    ip_address = models.GenericIPAddressField("IP адрес", null=True, blank=True)
    user_agent = models.TextField("User Agent", blank=True)
    
    # Дополнительные данные для аудита
    previous_data = models.JSONField("Предыдущие данные", null=True, blank=True)
    new_data = models.JSONField("Новые данные", null=True, blank=True)
    
    class Meta:
        verbose_name = "Лог архивирования"
        verbose_name_plural = "Логи архивирования"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.content_type.model} #{self.object_id}"


class ArchiveConfiguration(models.Model):
    """
    Конфигурация архивирования для разных моделей
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, unique=True)
    is_archivable = models.BooleanField("Поддерживает архивирование", default=True)
    cascade_archive = models.BooleanField("Каскадное архивирование", default=True)
    cascade_restore = models.BooleanField("Каскадное восстановление", default=True)
    auto_archive_related = models.BooleanField("Автоархивирование связанных", default=True)
    archive_after_days = models.PositiveIntegerField("Автоархивирование через дней", null=True, blank=True)
    
    # Настройки отображения
    show_archived_in_list = models.BooleanField("Показывать в списке", default=True)
    show_archived_in_search = models.BooleanField("Показывать в поиске", default=False)
    allow_restore = models.BooleanField("Разрешить восстановление", default=True)
    require_reason = models.BooleanField("Требовать причину", default=True)
    
    # Права доступа
    archive_permission = models.CharField("Разрешение на архивирование", max_length=100, blank=True)
    restore_permission = models.CharField("Разрешение на восстановление", max_length=100, blank=True)
    
    class Meta:
        verbose_name = "Конфигурация архивирования"
        verbose_name_plural = "Конфигурации архивирования"
        ordering = ['content_type__app_label', 'content_type__model']

    def __str__(self):
        return f"Архивирование {self.content_type}"

    @classmethod
    def get_config(cls, model):
        """
        Получает конфигурацию для модели
        """
        content_type = ContentType.objects.get_for_model(model)
        config, created = cls.objects.get_or_create(
            content_type=content_type,
            defaults={
                'is_archivable': True,
                'cascade_archive': True,
                'cascade_restore': True,
                'auto_archive_related': True,
                'show_archived_in_list': True,
                'show_archived_in_search': False,
                'allow_restore': True,
                'require_reason': True,
            }
        )
        return config 