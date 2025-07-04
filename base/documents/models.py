from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# 1. Новая модель для описания структуры документа
class DocumentType(models.Model):
    """
    Определяет тип и структуру документа через JSON-схему.
    Заменяет старую модель DocumentCategory.
    """
    name = models.CharField("Название типа документа", max_length=255, unique=True)
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_types',
        verbose_name="Отделение (опционально)"
    )
    # Здесь хранится схема для генерации формы
    schema = models.JSONField("Схема полей документа (JSON)", help_text="Описывает поля, их типы и метки")

    class Meta:
        verbose_name = "Тип документа"
        verbose_name_plural = "Типы документов"
        ordering = ['department__name', 'name']

    def __str__(self):
        if self.department:
            return f"{self.name} ({self.department.name})"
        return self.name

# 2. Обновленная модель для хранения экземпляров документов
class ClinicalDocument(models.Model):
    """
    Хранит экземпляр документа. Данные хранятся в поле JSON.
    """
    # Связь с типом документа, который определяет его структуру
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, verbose_name="Тип документа")
    
    # Метаданные документа (остаются как были)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    author_position = models.CharField("Должность автора", max_length=255, blank=True, null=True)
    datetime_document = models.DateTimeField("Дата документа", default=timezone.now)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    is_signed = models.BooleanField("Подписан", default=False)
    is_canceled = models.BooleanField("Аннулирован", default=False)

    # Здесь хранятся все введенные пользователем данные
    data = models.JSONField("Данные документа", default=dict)

    class Meta:
        verbose_name = "Клинический документ"
        verbose_name_plural = "Клинические документы"
        ordering = ["-datetime_document"]

    def __str__(self):
        return f"{self.document_type.name} от {self.datetime_document.strftime('%d.%m.%Y')}"

# 3. Обновленная модель для шаблонов
class DocumentTemplate(models.Model):
    """
    Шаблон с предзаполненными данными для определенного типа документа.
    """
    name = models.CharField("Название шаблона", max_length=255)
    # Шаблон теперь жестко привязан к типу документа
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='templates')
    
    # Метаданные шаблона
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Автор шаблона"
    )
    is_global = models.BooleanField("Общий шаблон", default=False)
    
    # Предзаполненные данные в формате JSON
    template_data = models.JSONField("Данные шаблона", default=dict)

    class Meta:
        verbose_name = "Шаблон документа"
        verbose_name_plural = "Шаблоны документов"
        # Шаблон должен быть уникальным для типа документа
        unique_together = ('name', 'document_type')

    def __str__(self):
        return f"Шаблон '{self.name}' для '{self.document_type.name}'"

# Модели DocumentCategory, NeonatalDailyNote и DocumentAttachment больше не нужны и удалены.
# Если нужна загрузка файлов, ее можно будет реализовать отдельно.