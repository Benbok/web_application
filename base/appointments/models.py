# appointments/models.py
from django.db import models
from django.conf import settings
from patients.models import Patient
import recurrence.fields

class Schedule(models.Model):
    """
    Расписание работы врача. Именно оно имеет повторяющуюся природу.
    """
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="schedules",
        limit_choices_to={"doctor_profile__isnull": False},
        verbose_name="Врач"
    )
    start_time = models.TimeField("Время начала смены")
    end_time = models.TimeField("Время окончания смены")
    duration = models.PositiveSmallIntegerField("Длительность приема (мин)", default=30)
    recurrences = recurrence.fields.RecurrenceField("Правило повторения")

    def __str__(self):
        return f"Расписание для {self.doctor.get_full_name()}"

    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписания"


class AppointmentEvent(models.Model):
    """
    Запись на прием. Это конкретное, единичное событие.
    """
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Слот расписания")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointment_events", verbose_name="Пациент")
    start = models.DateTimeField("Начало приема")
    end = models.DateTimeField("Конец приема")
    notes = models.TextField("Заметки", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[("scheduled", "Запланирован"), ("completed", "Завершен"), ("canceled", "Отменен")],
        default="scheduled"
    )

    @property
    def doctor(self):
        return self.schedule.doctor

    def __str__(self):
        return f"Прием у врача {self.doctor.get_full_name()} для {self.patient.full_name} в {self.start}"

    class Meta:
        verbose_name = "Запись на прием"
        verbose_name_plural = "Записи на прием"