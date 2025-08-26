from django.db import models
from django.contrib.auth.models import User
from base.models import TimeStampedModel

# Create your models here.

class UserProfile(TimeStampedModel):
    """Расширенный профиль пользователя для аутентификации"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Табельный номер"
    )
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.PROTECT,
        verbose_name="Отделение",
        null=True,
        blank=True
    )
    position = models.CharField(
        max_length=100,
        verbose_name="Должность"
    )
    phone = models.CharField(
        max_length=20,
        verbose_name="Телефон",
        blank=True
    )
    is_active_employee = models.BooleanField(
        default=True,
        verbose_name="Активный сотрудник"
    )
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"
    
    def get_full_name(self):
        """Получить полное имя пользователя"""
        if hasattr(self.user, 'doctor_profile'):
            return self.user.doctor_profile.full_name
        return self.user.get_full_name() or self.user.username
    
    def get_position(self):
        """Получить текущую должность"""
        if hasattr(self.user, 'doctor_profile'):
            return self.user.doctor_profile.get_current_position()
        return self.position
    
    def get_department(self):
        """Получить отделение"""
        if hasattr(self.user, 'doctor_profile'):
            # Здесь можно добавить логику получения отделения из DoctorProfile
            return self.department
        return self.department
