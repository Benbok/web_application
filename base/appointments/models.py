# appointments/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from patients.models import Patient

# Используем TextChoices для статусов — это читаемо и надежно
class AppointmentStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Запланирован'
    COMPLETED = 'completed', 'Завершен'
    CANCELED = 'canceled', 'Отменен'

class Schedule(models.Model):
    """
    Модель для РЕГУЛЯРНОГО расписания врача.
    Например: ПН 9:00-18:00, ВТ 9:00-18:00.
    """
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='schedules',
        # Предполагаем, что у User есть связь doctor_profile, как мы выяснили ранее
        limit_choices_to={'doctor_profile__isnull': False} 
    )
    appointment_duration = models.PositiveSmallIntegerField(
        "Длительность приема (мин)",
        default=30,
        help_text="Стандартная продолжительность одного приема в минутах."
    )

    # Django `weekday`: 0=ПН, 1=ВТ, ..., 6=ВС
    day_of_week = models.PositiveSmallIntegerField("День недели", choices=[(i, ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][i]) for i in range(7)])
    start_time = models.TimeField("Время начала работы")
    end_time = models.TimeField("Время окончания работы")

    class Meta:
        verbose_name = "График работы"
        verbose_name_plural = "Графики работы"
        unique_together = ('doctor', 'day_of_week') # У врача может быть только одна запись на день

    def __str__(self):
        return f"График Dr. {self.doctor.last_name}: {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"

class Appointment(models.Model):
    """
    Улучшенная модель записи на прием.
    """
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name="Пациент"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='doctor_appointments',
        limit_choices_to={'doctor_profile__isnull': False}
    )
    start_datetime = models.DateTimeField("Начало приема")
    end_datetime = models.DateTimeField("Конец приема")
    status = models.CharField(
        "Статус", 
        max_length=20, 
        choices=AppointmentStatus.choices, 
        default=AppointmentStatus.SCHEDULED
    )
    notes = models.TextField("Заметки пациента", blank=True, null=True)

    def __str__(self):
        return f"Прием у Dr. {self.doctor.last_name} для {self.patient.full_name}"

