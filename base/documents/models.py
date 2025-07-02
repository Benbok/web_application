# models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType



class DocumentCategory(models.Model):
    name = models.CharField("Название категории", max_length=100)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )
    department = models.ForeignKey('departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_categories',
        verbose_name="Отделение"
    )
    # Поле для указания, является ли эта категория конечным типом документа, к которому можно привязать шаблон/документ
    is_leaf_node = models.BooleanField("Является конечной категорией", default=True) 
    
    class Meta:
        verbose_name = "Категория документа"
        verbose_name_plural = "Категории документов"
        # Уникальность имени категории в рамках родителя и отделения
        unique_together = ('name', 'parent', 'department') 
        ordering = ['department__name', 'parent__name', 'name']

    def __str__(self):
        full_path = self.name
        current = self
        while current.parent:
            full_path = f"{current.parent.name} -> {full_path}"
            current = current.parent
        if self.department:
            return f"[{self.department.name}] {full_path}"
        return full_path

    # Метод для получения полного пути категории (для отображения)
    def get_full_path(self):
        path = [self.name]
        current = self
        while current.parent:
            current = current.parent
            path.insert(0, current.name)
        return " -> ".join(path)


class DocumentTemplate(models.Model):

    name = models.CharField("Название шаблона", max_length=100)
    # Теперь шаблон привязывается к конкретной категории документа из дерева
    document_category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        limit_choices_to={'is_leaf_node': True},
        verbose_name="Категория документа"
    )
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
        ordering = ["document_category__name", "name"] # Сортируем по новой категории

    def __str__(self):
        category_name = self.document_category.get_full_path() if self.document_category else "Без категории"
        visibility = "(общий)" if self.is_global else f"(личный: {self.author})"
        return f"{self.name} [{category_name}] {visibility}"


class ClinicalDocument(models.Model):

    # Поля для связи с другими моделями через GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) 
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    # Теперь документ привязывается к конкретной категории документа из дерева
    document_category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clinical_documents',
        limit_choices_to={'is_leaf_node': True}, # Документы привязываются только к конечным категориям
        verbose_name="Категория документа"
    )
    datetime_document = models.DateTimeField("Дата документа")
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
        category_name = self.document_category.get_full_path() if self.document_category else "Без категории"
        return f"{category_name} - {self.title} ({self.created_at.strftime('%d.%m.%Y')})"


class NeonatalDailyNote(models.Model):
    """
    Модель для детализированных записей ежедневного дневника наблюдения новорожденного.
    """
    # Теперь связь не с document_type, а с конкретной категорией
    # Это поле не будет 'OneToOneField' с ClinicalDocument, а будет связано через generic relationship
    # или, что проще, NeonatalDailyNote будет содержать все поля ClinicalDocument, которые она раньше имела
    # и больше не будет отдельной моделью, а будет инкорпорирована в ClinicalDocument.
    # Но для сохранения идеи "дневника" как отдельной модели, оставим OneToOneField, 
    # но изменим его для использования новой структуры.
    document = models.OneToOneField(
        ClinicalDocument, 
        on_delete=models.CASCADE, 
        related_name='neonatal_daily_note',
        # Дополнительная проверка на категорию, если нужно, но в основном это будет через фронтенд/формы
        # limit_choices_to={'document_category__name': 'Ежедневный дневник'}, # Пример, если имя категории строго фиксировано
        verbose_name="Медицинский документ (Дневник наблюдения)"
    )
    
    age_in_days = models.PositiveIntegerField("Возраст ребенка в сутках жизни")
    pkv = models.CharField("ПКВ (для недоношенных)", max_length=50, blank=True, null=True)
    
    # Витальные показатели
    temperature = models.DecimalField("Температура тела (°C)", max_digits=4, decimal_places=1, blank=True, null=True)
    respiratory_rate = models.PositiveIntegerField("Частота дыхания (ЧД)", blank=True, null=True)
    heart_rate = models.PositiveIntegerField("Частота сердечных сокращений (ЧСС)", blank=True, null=True)
    blood_pressure_systolic = models.PositiveIntegerField("Систолическое АД", blank=True, null=True)
    blood_pressure_diastolic = models.PositiveIntegerField("Диастолическое АД", blank=True, null=True)
    blood_pressure_mean = models.PositiveIntegerField("Среднее АД", blank=True, null=True)
    saturation = models.DecimalField("Сатурация (%)", max_digits=4, decimal_places=1, blank=True, null=True)

    # Респираторная терапия
    respiratory_therapy_type = models.CharField(
        "Вид респираторной терапии", 
        max_length=50, 
        blank=True, 
        null=True,
        choices=[
            ('IVL', 'ИВЛ'),
            ('VCHO_IVL', 'ВЧО ИВЛ'),
            ('NCPAP', 'NСРАР'),
            ('oxygen_therapy', 'Оксигенотерапия'),
        ]
    )
    ventilator_device = models.CharField("Аппарат ИВЛ", max_length=100, blank=True, null=True)
    ventilation_mode = models.CharField("Режим вентиляции", max_length=50, blank=True, null=True)
    respiratory_parameters = models.TextField("Основные параметры респираторной терапии (FiO2, Flow, PIP, PEEP, MAP, Tin, DO и т.д.)", blank=True, null=True)

    # Оценка состояния и динамика
    severity_assessment = models.TextField("Оценка тяжести состояния", blank=True, null=True)
    content = models.TextField("Содержимое дневника (основные наблюдения)", blank=True, null=True)
    
    # Заключение и план
    conclusion = models.TextField("Заключение (выводы о ведущих проблемах)", blank=True, null=True)
    management_plan = models.TextField("План ведения ребенка на сутки", blank=True, null=True)

    class Meta:
        verbose_name = "Дневник наблюдения новорожденного"
        verbose_name_plural = "Дневники наблюдения новорожденных"
        ordering = ["-age_in_days"]

    def __str__(self):
        return f"Дневник новорожденного от {(self.document.datetime_document).strftime('%d.%m.%Y %H:%M')}"


class DocumentAttachment(models.Model):
    document = models.ForeignKey(ClinicalDocument, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField("Файл", upload_to="documents/attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Вложение к документу"
        verbose_name_plural = "Вложения к документам"

    def __str__(self):
        return f"Файл от {self.uploaded_at.strftime('%d.%m.%Y')}"