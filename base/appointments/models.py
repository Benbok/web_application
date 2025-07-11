from django.db import models
from django.conf import settings
from django.utils import timezone
from patients.models import Patient
import recurrence.fields

class AppointmentStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Запланирован"
    COMPLETED = "completed", "Завершен"
    CANCELED = "canceled", "Отменен"

class Schedule(models.Model):
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

    @property
    def doctor_full_name(self):
        """Полное имя врача для расписания."""
        if self.doctor and hasattr(self.doctor, 'doctor_profile') and self.doctor.doctor_profile:
            return self.doctor.doctor_profile.full_name
        return None

    def __str__(self):
        start = self.start_time.strftime('%H:%M')
        end = self.end_time.strftime('%H:%M')

        # Получаем ФИО врача из DoctorProfile
        if self.doctor and hasattr(self.doctor, 'doctor_profile') and self.doctor.doctor_profile:
            doctor_name = self.doctor.doctor_profile.full_name
        else:
            doctor_name = self.doctor.username if self.doctor else "Неизвестный врач"

        return f"Расписание {doctor_name} ({start}—{end}, {self.duration} мин)"

    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписания"

class AppointmentEvent(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Слот расписания")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointment_events", verbose_name="Пациент")
    start = models.DateTimeField("Начало приема")
    end = models.DateTimeField("Конец приема")
    notes = models.TextField("Заметки", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED
    )

    @property
    def doctor(self):
        """Безопасный доступ к врачу через расписание."""
        return self.schedule.doctor if self.schedule else None

    def __str__(self):
        """Безопасный и устойчивый метод представления записи."""
        # Полностью безопасный доступ, без вызова @property
        doctor_name = "Неизвестный врач"
        if self.schedule and self.schedule.doctor:
            doctor_name = self.schedule.doctor.get_full_name()

        patient_name = getattr(self.patient, 'full_name', "Неизвестный пациент")
        return f"Прием у врача {doctor_name} для {patient_name} в {self.start}"

    def is_upcoming(self):
        return self.start > timezone.now()

    def is_completed(self):
        return self.status == AppointmentStatus.COMPLETED

    class Meta:
        verbose_name = "Запись на прием"
        verbose_name_plural = "Записи на прием"
