from django.db import models
from django.conf import settings
from patients.models import Patient
import recurrence.fields

class AppointmentEvent(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
        limit_choices_to={"doctor_profile__isnull": False}
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="events"
    )
    start = models.DateTimeField("Начало события")
    end = models.DateTimeField("Конец события")
    notes = models.TextField("Заметки", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("scheduled", "Запланирован"),
            ("completed", "Завершен"),
            ("canceled", "Отменен")
        ],
        default="scheduled"
    )
    recurrence = recurrence.fields.RecurrenceField(blank=True, null=True)

    def __str__(self):
        return f"Прием у Dr. {self.doctor.get_full_name()} для {self.patient.full_name}"