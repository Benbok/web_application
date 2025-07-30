# pharmacy/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from diagnosis.models import Diagnosis 
from patients.models import Patient 

class MedicationGroup(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name=_("Название группы"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание группы"))
    class Meta:
        verbose_name = _("Группа препаратов")
        verbose_name_plural = _("Группы препаратов")
        ordering = ['name']
    def __str__(self):
        return self.name

class ReleaseForm(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название формы выпуска"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание формы выпуска"))
    class Meta:
        verbose_name = _("Форма выпуска")
        verbose_name_plural = _("Формы выпуска")
        ordering = ['name']
    def __str__(self):
        return self.name

class AdministrationMethod(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название способа введения"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание способа введения"))
    class Meta:
        verbose_name = _("Способ введения")
        verbose_name_plural = _("Способы введения")
        ordering = ['name']
    def __str__(self):
        return self.name

class Medication(models.Model):
    """
    Модель-справочник. Хранит только основную информацию о препарате.
    """
    name = models.CharField("Название препарата (МНН)", max_length=255, unique=True,
                            help_text="Международное непатентованное наименование")
    
    # Ссылка на внешний источник полной информации
    external_info_url = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Ссылка на полную информацию о препарате"))

    class Meta:
        verbose_name = "Препарат"
        verbose_name_plural = "Препараты"
        ordering = ['name']

    def __str__(self):
        return self.name

class TradeName(models.Model):
    """Торговое наименование препарата."""
    
    name = models.CharField("Торговое название", max_length=255)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='trade_names',
                                   verbose_name="Активное вещество (МНН)")
    # Ссылка на внешний источник полной информации
    external_info_url = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Ссылка на полную информацию о препарате"))

    # Классификация и форма выпуска
    medication_group = models.ForeignKey(MedicationGroup, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='medications', verbose_name=_("Фармакологическая группа"))
    atc_code = models.CharField(max_length=10, blank=True, null=True, verbose_name=_("АТХ код"))

    release_form = models.ForeignKey(ReleaseForm, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='medications', verbose_name=_("Лекарственная форма"))
    
    class Meta:
        verbose_name = "Торговое наименование"
        verbose_name_plural = "Торговые наименования"

    def __str__(self):
        return f"{self.name} ({self.medication.name})"

class Regimen(models.Model):
    """
    Схема (режим) применения препарата для определённого клинического случая.
    Это центральная модель, объединяющая показания, критерии и дозировки.
    """
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='regimens',
                                   verbose_name=_("Препарат (МНН)"))
    
    name = models.CharField(_("Название схемы"), max_length=255, 
                            help_text=_("Напр., 'Стандартная терапия для взрослых' или 'Терапия неосложненной гонореи'"))

    indications = models.ManyToManyField(Diagnosis, related_name='regimens', 
                                         verbose_name=_("Показания (Диагнозы)"),
                                         help_text=_("Диагнозы, при которых применяется эта схема"))

    notes = models.TextField(_("Общие примечания к схеме"), blank=True, null=True)

    class Meta:
        verbose_name = _("Схема применения")
        verbose_name_plural = _("Схемы применения")
        ordering = ['medication', 'name']

    def __str__(self):
        return f"{self.medication.name} - {self.name}"


class PopulationCriteria(models.Model):
    """
    Описывает целевую группу пациентов для конкретной схемы применения.
    У одной схемы может быть несколько наборов критериев.
    """
    regimen = models.ForeignKey(Regimen, on_delete=models.CASCADE, related_name='population_criteria',
                                verbose_name=_("Схема применения"))
    
    name = models.CharField(_("Название группы пациентов"), max_length=255, default="Основная группа",
                            help_text=_("Напр., 'Взрослые и дети > 12 лет', 'Дети 6-12 лет'"))

    min_age_days = models.PositiveIntegerField(_("Минимальный возраст (дней)"), blank=True, null=True)
    max_age_days = models.PositiveIntegerField(_("Максимальный возраст (дней)"), blank=True, null=True)

    min_weight_kg = models.DecimalField(_("Минимальный вес (кг)"), max_digits=5, decimal_places=2, blank=True, null=True)
    max_weight_kg = models.DecimalField(_("Максимальный вес (кг)"), max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Критерии пациента")
        verbose_name_plural = _("Критерии пациентов")

    def __str__(self):
        return f"{self.regimen} - {self.name}"

    def clean(self):
        if self.min_age_days and self.max_age_days:
            if self.min_age_days > self.max_age_days:
                raise ValidationError("Минимальный возраст не может быть больше максимального")


class DosingInstruction(models.Model):
    """
    Конкретная инструкция по дозированию в рамках одной схемы.
    """
    regimen = models.ForeignKey(Regimen, on_delete=models.CASCADE, related_name='dosing_instructions',
                                verbose_name=_("Схема применения"))

    DOSE_TYPE_CHOICES = [
        ('MAINTENANCE', _('Поддерживающая')),
        ('LOADING', _('Нагрузочная')),
        ('SINGLE', _('Однократная')),
    ]
    dose_type = models.CharField(_("Тип дозы"), max_length=20, choices=DOSE_TYPE_CHOICES, default='MAINTENANCE')

    # Использование текстового поля дает гибкость для описания сложных доз
    dose_description = models.CharField(_("Описание дозы"), max_length=255, 
                                        help_text=_("Напр., '400 мг' или '8 мг/кг массы тела'"))
    
    frequency_description = models.CharField(_("Описание частоты"), max_length=255, 
                                             help_text=_("Напр., '1 раз/сутки' или 'по 200 мг каждые 12 ч'"))

    duration_description = models.CharField(_("Описание длительности"), max_length=255,
                                            help_text=_("Напр., '7-10 дней' или 'не менее 10 дней'"))

    route = models.ForeignKey(AdministrationMethod, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_("Путь введения"))

    class Meta:
        verbose_name = _("Инструкция по дозированию")
        verbose_name_plural = _("Инструкции по дозированию")

    def __str__(self):
        return f"{self.regimen} - {self.dose_description}"


class RegimenAdjustment(models.Model):
    """
    Корректировка базовой схемы при определённых условиях.
    """
    regimen = models.ForeignKey(Regimen, on_delete=models.CASCADE, related_name='adjustments',
                                verbose_name=_("Схема применения"))

    condition = models.CharField(_("Условие для корректировки"), max_length=255, 
                                 help_text=_("Напр., 'При КК от 21 до 60 мл/мин' или 'Пациенты на гемодиализе'"))

    adjustment_description = models.CharField(_("Описание корректировки"), max_length=255,
                                              help_text=_("Напр., 'суточную дозу следует уменьшить на 25%'"))
    
    class Meta:
        verbose_name = _("Корректировка схемы")
        verbose_name_plural = _("Корректировки схем")

    def __str__(self):
        return f"Корректировка для '{self.regimen.name}'"