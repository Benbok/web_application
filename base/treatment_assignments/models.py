# treatment_assignments/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from patients.models import Patient
from pharmacy.models import Medication, DosingRule
 
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition

class BaseAssignment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name="Пациент")
    assigning_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Назначивший врач")
    start_date = models.DateTimeField("Дата и время назначения", null=False, blank=False)
    end_date = models.DateTimeField("Дата и время завершения", null=True, blank=True)
    notes = models.TextField("Примечания", blank=True, null=True)
    cancellation_reason = models.TextField("Причина отмены", blank=True, null=True)

    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('canceled', 'Отменено'),
        ('paused', 'Приостановлено'),
    ]
    status = models.CharField("Статус", max_length=10, choices=STATUS_CHOICES, default='active')
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Завершено кем", related_name='+')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        abstract = True
        ordering = ['-start_date']


class MedicationAssignment(BaseAssignment):
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, verbose_name="Препарат")

    dosing_rule = models.ForeignKey('pharmacy.DosingRule', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name="Правило дозирования")
    duration_days = models.PositiveIntegerField("Длительность (дней)", null=True, blank=True,
                                                help_text="Укажите длительность курса в днях")

    patient_weight = models.DecimalField("Вес пациента (кг)", max_digits=5, decimal_places=2, blank=True, null=True)

    assigning_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Назначивший врач", related_name='medication_assigned_treatments')
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Завершено кем", related_name='medication_completed_treatments')

    @property
    def assignment_type(self):
        return 'medication'

    @property
    def treatment_name(self):
        return self.medication.name

    def get_absolute_url(self):
        return reverse('treatment_assignments:assignment_detail',
                       kwargs={'assignment_type': 'medication', 'pk': self.pk})

    def get_update_url(self):
        return reverse('treatment_assignments:assignment_update',
                       kwargs={'assignment_type': 'medication', 'pk': self.pk})

    class Meta:
        verbose_name = "Назначение препарата"
        verbose_name_plural = "Назначения препаратов"


class GeneralTreatmentAssignment(BaseAssignment):
    general_treatment = models.TextField("Общее назначение")

    assigning_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Назначивший врач", related_name='general_assigned_treatments')
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Завершено кем", related_name='general_completed_treatments')

    @property
    def assignment_type(self):
        return 'general'

    def get_absolute_url(self):
        return reverse('treatment_assignments:assignment_detail', kwargs={'assignment_type': self.assignment_type, 'pk': self.pk})

    def get_update_url(self):
        return reverse('treatment_assignments:assignment_update', kwargs={'assignment_type': self.assignment_type, 'pk': self.pk})

    class Meta(BaseAssignment.Meta):
        verbose_name = "Общее назначение"
        verbose_name_plural = "Общие назначения"

    def __str__(self):
        return f"Общее назначение '{self.general_treatment}' от {self.start_date.strftime('%d.%m.%Y')}"


class LabTestAssignment(BaseAssignment):
    lab_test = models.ForeignKey(LabTestDefinition, on_delete=models.PROTECT, related_name='lab_assignments', verbose_name="Лабораторное исследование")

    assigning_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Назначивший врач", related_name='lab_assigned_treatments')
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Завершено кем", related_name='lab_completed_treatments')

    @property
    def treatment_name(self):
        return self.lab_test.name

    @property
    def assignment_type(self):
        return 'lab'

    def get_absolute_url(self):
        return reverse('treatment_assignments:assignment_detail', kwargs={'assignment_type': self.assignment_type, 'pk': self.pk})

    def get_update_url(self):
        return reverse('treatment_assignments:assignment_update', kwargs={'assignment_type': self.assignment_type, 'pk': self.pk})

    class Meta(BaseAssignment.Meta):
        verbose_name = "Назначение лабораторного исследования"
        verbose_name_plural = "Назначения лабораторных исследований"

    def __str__(self):
        return f"Лаб. исследование '{self.treatment_name}' от {self.start_date.strftime('%d.%m.%Y')}"


class InstrumentalProcedureAssignment(BaseAssignment):
    instrumental_procedure = models.ForeignKey(InstrumentalProcedureDefinition, on_delete=models.PROTECT, related_name='instrumental_assignments', verbose_name="Инструментальное исследование")

    assigning_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Назначивший врач", related_name='instrumental_assigned_treatments')
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Завершено кем", related_name='instrumental_completed_treatments')

    @property
    def treatment_name(self):
        return self.instrumental_procedure.name

    @property
    def assignment_type(self):
        return 'instrumental'

    def get_absolute_url(self):
        return reverse('treatment_assignments:assignment_detail', kwargs={'assignment_type': self.assignment_type, 'pk': self.pk})

    def get_update_url(self):
        return reverse('treatment_assignments:assignment_update', kwargs={'assignment_type': self.assignment_type, 'pk': self.pk})

    class Meta(BaseAssignment.Meta):
        verbose_name = "Назначение инструментального исследования"
        verbose_name_plural = "Назначения инструментальных исследований"

    def __str__(self):
        return f"Инстр. исследование '{self.treatment_name}' от {self.start_date.strftime('%d.%m.%Y')}"
