from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from pharmacy.models import Medication


class TreatmentPlan(models.Model):
    """
    Универсальный план лечения, который может быть привязан к любому объекту
    (encounter, department_stay, etc.)
    """
    name = models.CharField(_("Название плана"), max_length=200)
    description = models.TextField(_("Описание"), blank=True)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)
    
    # GenericForeignKey для связи с любым объектом
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    owner = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        verbose_name = _("План лечения")
        verbose_name_plural = _("Планы лечения")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.owner})"
    
    def clean(self):
        """Проверка, что owner существует"""
        if not self.owner:
            raise ValidationError(_("Владелец плана лечения должен быть указан"))
    
    def get_owner_display(self):
        """Возвращает читаемое представление владельца"""
        if hasattr(self.owner, 'get_display_name'):
            return self.owner.get_display_name()
        return str(self.owner)
    
    def get_owner_model_name(self):
        """Возвращает имя модели владельца для использования в шаблонах"""
        return self.owner._meta.model_name
    
    @classmethod
    def get_or_create_main_plan(cls, owner):
        """
        Получает или создает основной план лечения для указанного владельца
        """
        content_type = ContentType.objects.get_for_model(owner)
        
        # Пытаемся найти существующий основной план
        main_plan, created = cls.objects.get_or_create(
            content_type=content_type,
            object_id=owner.id,
            name="Основной",
            defaults={
                'description': 'Основной план лечения'
            }
        )
        
        return main_plan, created


class TreatmentMedication(models.Model):
    """
    Лекарство в плане лечения
    """
    
    treatment_plan = models.ForeignKey(
        TreatmentPlan, 
        on_delete=models.CASCADE, 
        related_name='medications',
        verbose_name=_("План лечения")
    )
    
    # Препарат из справочника или собственный
    medication = models.ForeignKey(
        Medication, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Препарат из справочника")
    )
    custom_medication = models.CharField(
        _("Собственный препарат"), 
        max_length=200, 
        blank=True,
        help_text=_("Введите название препарата, если его нет в справочнике")
    )
    
    # Параметры назначения
    dosage = models.CharField(_("Дозировка"), max_length=100)
    frequency = models.CharField(_("Частота приема"), max_length=100)
    route = models.ForeignKey(
        'pharmacy.AdministrationMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Способ введения"),
        help_text=_("Выберите способ введения препарата")
    )
    duration = models.CharField(_("Длительность"), max_length=100, blank=True)
    instructions = models.TextField(_("Особые указания"), blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)
    
    class Meta:
        verbose_name = _("Лекарство в плане лечения")
        verbose_name_plural = _("Лекарства в планах лечения")
        ordering = ['-created_at']
    
    def __str__(self):
        medication_name = self.get_medication_name()
        return f"{medication_name} - {self.dosage} {self.frequency}"
    
    def clean(self):
        """Проверка, что указан либо препарат из справочника, либо собственный"""
        if not self.medication and not self.custom_medication:
            raise ValidationError(
                _("Необходимо указать либо препарат из справочника, либо собственный препарат")
            )
        if self.medication and self.custom_medication:
            raise ValidationError(
                _("Нельзя указывать одновременно препарат из справочника и собственный препарат")
            )
    
    def get_medication_name(self):
        """Возвращает название препарата"""
        if self.medication:
            return self.medication.name
        return self.custom_medication
    
    def get_route_display_name(self):
        """Возвращает читаемое название способа введения"""
        if self.route:
            return self.route.name
        return _("Не указан")
    
    def get_external_info_url(self):
        """Возвращает ссылку на внешнюю информацию о препарате"""
        if self.medication and self.medication.external_info_url:
            return self.medication.external_info_url
        return None
    
    def get_medication_form(self):
        """Возвращает лекарственную форму препарата"""
        if self.medication and hasattr(self.medication, 'medication_form'):
            return self.medication.medication_form
        return None


class TreatmentRecommendation(models.Model):
    """
    Рекомендации в плане лечения
    """
    treatment_plan = models.ForeignKey(
        TreatmentPlan, 
        on_delete=models.CASCADE, 
        related_name='recommendations',
        verbose_name=_("План лечения")
    )
    
    text = models.TextField(_("Текст рекомендации"), help_text=_("Введите рекомендацию"))
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)
    
    class Meta:
        verbose_name = _("Рекомендация в плане лечения")
        verbose_name_plural = _("Рекомендации в планах лечения")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.text[:50]}..." if len(self.text) > 50 else self.text