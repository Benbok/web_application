"""
Улучшенные модели для модуля Documents
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.cache import cache
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
import json
import hashlib

from .optimizations import DocumentQuerySet, DocumentIndexes


class DocumentType(models.Model):
    """
    Улучшенная модель типа документа с кэшированием и валидацией
    """
    name = models.CharField("Название типа документа", max_length=255)
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_types',
        verbose_name="Отделение (опционально)"
    )
    schema = models.JSONField("Схема полей документа (JSON)")
    
    # Новые поля для улучшений
    is_active = models.BooleanField("Активен", default=True)
    version = models.PositiveIntegerField("Версия схемы", default=1)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    
    # Кэш для хеша схемы
    _schema_hash = None
    
    class Meta:
        verbose_name = "Тип документа"
        verbose_name_plural = "Типы документов"
        ordering = ['department__name', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['department', 'is_active']),
        ]

    def __str__(self):
        if self.department:
            return f"{self.name} ({self.department.name})"
        return self.name
    
    @property
    def schema_hash(self):
        """
        Возвращает хеш схемы для кэширования
        """
        if self._schema_hash is None:
            schema_str = json.dumps(self.schema, sort_keys=True)
            self._schema_hash = hashlib.md5(schema_str.encode()).hexdigest()
        return self._schema_hash
    
    def save(self, *args, **kwargs):
        """
        Переопределяем save для инвалидации кэша
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Инвалидируем кэш форм при изменении схемы
        if not is_new:
            from .optimizations import DocumentOptimizations
            DocumentOptimizations.invalidate_form_cache(self.pk)
    
    def get_field_names(self):
        """
        Возвращает список имен полей из схемы
        """
        return [field.get('name') for field in self.schema.get('fields', [])]
    
    def validate_schema(self):
        """
        Валидация JSON-схемы
        """
        if not isinstance(self.schema, dict):
            raise ValueError("Схема должна быть словарем")
        
        if 'fields' not in self.schema:
            raise ValueError("Схема должна содержать поле 'fields'")
        
        for field in self.schema['fields']:
            if not isinstance(field, dict):
                raise ValueError("Каждое поле должно быть словарем")
            
            if 'name' not in field or 'type' not in field:
                raise ValueError("Каждое поле должно содержать 'name' и 'type'")


class ClinicalDocument(models.Model):
    """
    Улучшенная модель клинического документа с оптимизациями
    """
    document_type = models.ForeignKey(
        DocumentType, 
        on_delete=models.PROTECT, 
        verbose_name="Тип документа"
    )
    
    # Метаданные
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='authored_documents'
    )
    author_position = models.CharField("Должность автора", max_length=255, blank=True, null=True)
    
    datetime_document = models.DateTimeField("Дата документа", default=timezone.now)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    
    # Статусы
    is_signed = models.BooleanField("Подписан", default=False)
    is_canceled = models.BooleanField("Аннулирован", default=False)
    is_archived = models.BooleanField("Архивирован", default=False)
    
    # Данные документа
    data = models.JSONField("Данные документа", default=dict)
    
    # Поисковый вектор для PostgreSQL
    data_search = SearchVectorField("Поиск по данным", null=True, blank=True)
    
    # Используем оптимизированный QuerySet
    objects = DocumentQuerySet.as_manager()
    
    class Meta:
        verbose_name = "Клинический документ"
        verbose_name_plural = "Клинические документы"
        ordering = ["-datetime_document"]
        indexes = DocumentIndexes.Meta.indexes + [
            # Дополнительные индексы
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['is_canceled', 'is_archived']),
            models.Index(fields=['created_at', 'updated_at']),
            # GIN индекс для поиска
            GinIndex(fields=['data_search'], name='document_search_gin_idx'),
        ]

    def __str__(self):
        return f"{self.document_type.name} от {self.datetime_document.strftime('%d.%m.%Y')}"
    
    def save(self, *args, **kwargs):
        """
        Переопределяем save для обновления поискового вектора
        """
        # Обновляем поисковый вектор
        from .optimizations import DocumentSearch
        self.data_search = DocumentSearch.create_search_vector(self)
        
        super().save(*args, **kwargs)
    
    @property
    def status(self):
        """
        Возвращает статус документа
        """
        if self.is_canceled:
            return "Аннулирован"
        elif self.is_archived:
            return "Архивирован"
        elif self.is_signed:
            return "Подписан"
        else:
            return "Черновик"
    
    def get_field_value(self, field_name):
        """
        Безопасное получение значения поля из JSON-данных
        """
        return self.data.get(field_name)
    
    def set_field_value(self, field_name, value):
        """
        Безопасная установка значения поля в JSON-данных
        """
        self.data[field_name] = value
    
    def validate_data_against_schema(self):
        """
        Валидация данных документа против схемы
        """
        schema_fields = self.document_type.get_field_names()
        data_fields = set(self.data.keys())
        
        # Проверяем обязательные поля
        for field in self.document_type.schema.get('fields', []):
            if field.get('required', False) and field['name'] not in data_fields:
                raise ValueError(f"Обязательное поле '{field['name']}' отсутствует")
        
        return True


class DocumentTemplate(models.Model):
    """
    Улучшенная модель шаблона документа
    """
    name = models.CharField("Название шаблона", max_length=255)
    document_type = models.ForeignKey(
        DocumentType, 
        on_delete=models.CASCADE, 
        related_name='templates'
    )
    
    # Метаданные
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Автор шаблона",
        related_name='created_templates'
    )
    is_global = models.BooleanField("Общий шаблон", default=False)
    is_active = models.BooleanField("Активен", default=True)
    
    # Данные шаблона
    template_data = models.JSONField("Данные шаблона", default=dict)
    
    # Метаданные шаблона
    description = models.TextField("Описание", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    usage_count = models.PositiveIntegerField("Количество использований", default=0)
    
    class Meta:
        verbose_name = "Шаблон документа"
        verbose_name_plural = "Шаблоны документов"
        unique_together = ('name', 'document_type')
        ordering = ['-usage_count', 'name']
        indexes = [
            models.Index(fields=['is_global', 'is_active']),
            models.Index(fields=['document_type', 'is_active']),
            models.Index(fields=['author', 'is_active']),
        ]

    def __str__(self):
        return f"Шаблон '{self.name}' для '{self.document_type.name}'"
    
    def increment_usage(self):
        """
        Увеличивает счетчик использований
        """
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def validate_template_data(self):
        """
        Валидация данных шаблона против схемы
        """
        schema_fields = self.document_type.get_field_names()
        template_fields = set(self.template_data.keys())
        
        # Проверяем, что все поля шаблона существуют в схеме
        invalid_fields = template_fields - set(schema_fields)
        if invalid_fields:
            raise ValueError(f"Поля шаблона не существуют в схеме: {invalid_fields}")
        
        return True


class DocumentVersion(models.Model):
    """
    Модель для версионирования документов
    """
    document = models.ForeignKey(
        ClinicalDocument,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField("Номер версии")
    
    # Данные версии
    data = models.JSONField("Данные версии")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    change_description = models.TextField("Описание изменений", blank=True)
    
    class Meta:
        verbose_name = "Версия документа"
        verbose_name_plural = "Версии документов"
        unique_together = ('document', 'version_number')
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['document', 'version_number']),
        ]

    def __str__(self):
        return f"Версия {self.version_number} документа {self.document.id}"


class DocumentAuditLog(models.Model):
    """
    Модель для аудита изменений документов
    """
    ACTION_CHOICES = [
        ('created', 'Создан'),
        ('updated', 'Обновлен'),
        ('deleted', 'Удален'),
        ('signed', 'Подписан'),
        ('canceled', 'Аннулирован'),
        ('archived', 'Архивирован'),
    ]
    
    document = models.ForeignKey(
        ClinicalDocument,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField("Действие", max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    timestamp = models.DateTimeField("Время", auto_now_add=True)
    ip_address = models.GenericIPAddressField("IP адрес", null=True, blank=True)
    user_agent = models.TextField("User Agent", blank=True)
    changes = models.JSONField("Изменения", default=dict, blank=True)
    
    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Записи аудита"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['document', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.document} ({self.timestamp})" 