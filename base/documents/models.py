from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class DocumentTemplate(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('inspection', 'Осмотр'),
        ('daily_note', 'Дневник наблюдения'),
        ('consultation', 'Консультация специалиста'),
        ('discharge_summary', 'Выписка'),
        ('epicrisis', 'Эпикриз'),
        ('transfer_note', 'Переводной эпикриз'),
    ]

    name = models.CharField("Название шаблона", max_length=100)
    document_type = models.CharField("Тип документа", max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    default_content = models.TextField("Содержимое по умолчанию")
    is_global = models.BooleanField("Общий шаблон", default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Автор шаблона"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Шаблон документа"
        verbose_name_plural = "Шаблоны документов"
        ordering = ["document_type", "name"]

    def __str__(self):
        visibility = "(общий)" if self.is_global else f"(личный: {self.author})"
        return f"{self.name} {visibility}"


class ClinicalDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = DocumentTemplate.DOCUMENT_TYPE_CHOICES

    # Поля для связи с другими моделями через GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) 
    # Поле для хранения ID объекта, к которому относится документ
    object_id = models.PositiveIntegerField()
    # GenericForeignKey для связи с любым объектом
    content_object = GenericForeignKey('content_type', 'object_id')
    
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    document_type = models.CharField("Тип документа", max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField("Заголовок", max_length=255)
    content = models.TextField("Содержимое")
    template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    is_signed = models.BooleanField("Подписан", default=False)
    is_canceled = models.BooleanField("Аннулирован", default=False)

    class Meta:
        verbose_name = "Медицинский документ"
        verbose_name_plural = "Медицинские документы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} ({self.created_at.strftime('%d.%m.%Y')})"


class DocumentAttachment(models.Model):
    document = models.ForeignKey(ClinicalDocument, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField("Файл", upload_to="documents/attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Вложение к документу"
        verbose_name_plural = "Вложения к документам"

    def __str__(self):
        return f"Файл от {self.uploaded_at.strftime('%d.%m.%Y')}"
