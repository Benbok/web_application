from django.db import models
from django.conf import settings
from django.utils import timezone

class DoctorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    full_name = models.CharField("ФИО", max_length=255)
    specialization = models.CharField("Специальность", max_length=255)
    position = models.CharField("Основная должность", max_length=255, blank=True, null=True)
    employment_date = models.DateField("Дата трудоустройства")
    dismissal_date = models.DateField("Дата увольнения", null=True, blank=True)

    class Meta:
        verbose_name = "Профиль врача"
        verbose_name_plural = "Профили врачей"

    def __str__(self):
        return f"Профиль {self.full_name}"

    def get_current_position(self, at_date=None):
        """
        Возвращает текущую активную должность врача на заданную дату.
        Если at_date не указана, используется текущая дата.
        """
        if at_date is None:
            at_date = timezone.now().date()

        # Ищем активную временную должность на заданную дату
        active_temp_position = self.temporary_positions.filter(
            start_date__lte=at_date,
            end_date__gte=at_date
        ).first()

        if active_temp_position:
            return active_temp_position.position_name
        
        # Если нет активной временной должности, возвращаем основную
        return self.position if self.position else self.specialization


class TemporaryPosition(models.Model):
    doctor_profile = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='temporary_positions')
    position_name = models.CharField("Название временной должности", max_length=255)
    start_date = models.DateField("Дата начала")
    end_date = models.DateField("Дата окончания")

    class Meta:
        verbose_name = "Временная должность"
        verbose_name_plural = "Временные должности"
        ordering = ['start_date']

    def __str__(self):
        return f"{self.position_name} ({self.start_date} - {self.end_date}) для {self.doctor_profile.full_name}"