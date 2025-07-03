# treatment_assignments/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from patients.models import Patient
from pharmacy.models import Medication # Импортируем новую модель Medication

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
    
    # Ссылка на препарат из аптеки
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT, # Не удаляем препарат, если есть назначения
        related_name='assignments',
        verbose_name="Препарат",
        blank=True, null=True # Разрешаем быть пустым
    )
    # Поля для конкретного назначения (могут отличаться от дефолтных в Medication)
    patient_weight = models.DecimalField("Вес пациента (кг)", max_digits=5, decimal_places=2, blank=True, null=True)
    dosage = models.CharField("Дозировка", max_length=100, blank=True, null=True)
    frequency = models.CharField("Частота", max_length=100, blank=True, null=True)
    duration = models.CharField("Длительность", max_length=100, blank=True, null=True)
    route = models.CharField("Путь введения", max_length=100, blank=True, null=True)
    notes = models.TextField("Примечания", blank=True, null=True)

    start_date = models.DateTimeField("Дата начала", null=False, blank=False)
    end_date = models.DateTimeField("Дата завершения", null=True, blank=True)
    
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
        return f"Назначение '{self.medication.name}' от {self.assignment_date.strftime('%d.%m.%Y')} для {self.patient.full_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('treatment_assignments:assignment_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if self.status == 'completed' and self.end_date is None:
            from django.utils import timezone
            self.end_date = timezone.now()
        elif self.status != 'completed':
            self.end_date = None
        super().save(*args, **kwargs)
