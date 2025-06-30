# treatment_assignments/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from patients.models import Patient
# from encounters.models import Encounter # Если планируете привязывать к случаям обращения
# from departments.models import PatientDepartmentStatus # Если планируете привязывать к статусу пациента в отделении

class TreatmentAssignment(models.Model):
    """
    Модель, представляющая назначение лечения.
    Может быть прикреплена к различным объектам (например, PatientDepartmentStatus, Encounter).
    """
    # Generic Foreign Key для привязки к любому объекту
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='treatment_assignments',
        verbose_name="Пациент"
    )
    assigning_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Назначивший врач"
    )
    assignment_date = models.DateTimeField(
        "Дата и время назначения",
        auto_now_add=True
    )
    treatment_name = models.CharField("Название лечения/препарата", max_length=255)
    dosage = models.CharField("Дозировка", max_length=100, blank=True, null=True)
    frequency = models.CharField("Частота", max_length=100, blank=True, null=True)
    duration = models.CharField("Длительность", max_length=100, blank=True, null=True)
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
        verbose_name = "Назначение лечения"
        verbose_name_plural = "Назначения лечения"
        ordering = ['-assignment_date']

    def __str__(self):
        return f"Назначение '{self.treatment_name}' от {self.assignment_date.strftime('%d.%m.%Y')} для {self.patient.full_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('treatment_assignments:assignment_detail', kwargs={'pk': self.pk})
