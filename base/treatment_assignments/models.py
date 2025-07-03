# treatment_assignments/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from patients.models import Patient
from pharmacy.models import Medication
from general_treatments.models import GeneralTreatmentDefinition
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition

# Базовый класс для всех типов назначений
class BaseAssignment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        verbose_name="Пациент"
    )
    assigning_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Назначивший врач"
    )
    start_date = models.DateTimeField("Дата начала", null=False, blank=False)
    end_date = models.DateTimeField("Дата завершения", null=True, blank=True)
    notes = models.TextField("Примечания", blank=True, null=True)

    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('canceled', 'Отменено'),
        ('paused', 'Приостановлено'),
    ]
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True # Это абстрактная модель, она не будет создаваться в БД
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        if self.status == 'completed' and self.end_date is None:
            from django.utils import timezone
            self.end_date = timezone.now()
        elif self.status != 'completed':
            self.end_date = None
        super().save(*args, **kwargs)


class MedicationAssignment(BaseAssignment):
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        related_name='medication_assignments',
        verbose_name="Препарат",
        blank=True, null=True
    )
    patient_weight = models.DecimalField("Вес пациента (кг)", max_digits=5, decimal_places=2, blank=True, null=True)
    dosage = models.CharField("Дозировка", max_length=100, blank=True, null=True)
    frequency = models.CharField("Частота", max_length=100, blank=True, null=True)
    duration = models.CharField("Длительность", max_length=100, blank=True, null=True)
    route = models.CharField("Путь введения", max_length=100, blank=True, null=True)

    class Meta(BaseAssignment.Meta):
        verbose_name = "Назначение препарата"
        verbose_name_plural = "Назначения препаратов"

    def __str__(self):
        return f"Назначение '{self.medication.name if self.medication else ''}' от {self.start_date.strftime('%d.%m.%Y')} для {self.patient.full_name}"


class GeneralTreatmentAssignment(BaseAssignment):
    general_treatment = models.ForeignKey(
        GeneralTreatmentDefinition,
        on_delete=models.PROTECT,
        related_name='general_assignments',
        verbose_name="Общее назначение"
    )
    # Дополнительные поля, специфичные для общих назначений, если нужны

    class Meta(BaseAssignment.Meta):
        verbose_name = "Общее назначение"
        verbose_name_plural = "Общие назначения"

    def __str__(self):
        return f"Общее назначение '{self.general_treatment.name}' от {self.start_date.strftime('%d.%m.%Y')}"


class LabTestAssignment(BaseAssignment):
    lab_test = models.ForeignKey(
        LabTestDefinition,
        on_delete=models.PROTECT,
        related_name='lab_assignments',
        verbose_name="Лабораторное исследование"
    )
    # Дополнительные поля, специфичные для лабораторных исследований, если нужны

    class Meta(BaseAssignment.Meta):
        verbose_name = "Назначение лабораторного исследования"
        verbose_name_plural = "Назначения лабораторных исследований"

    def __str__(self):
        return f"Лаб. исследование '{self.lab_test.name}' от {self.start_date.strftime('%d.%m.%Y')}"


class InstrumentalProcedureAssignment(BaseAssignment):
    instrumental_procedure = models.ForeignKey(
        InstrumentalProcedureDefinition,
        on_delete=models.PROTECT,
        related_name='instrumental_assignments',
        verbose_name="Инструментальное исследование"
    )
    # Дополнительные поля, специфичные для инструментальных исследований, если нужны

    class Meta(BaseAssignment.Meta):
        verbose_name = "Назначение инструментального исследования"
        verbose_name_plural = "Назначения инструментальных исследований"

    def __str__(self):
        return f"Инстр. исследование '{self.instrumental_procedure.name}' от {self.start_date.strftime('%d.%m.%Y')}"
