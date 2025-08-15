# departments/models.py
from django.db import models
from patients.models import Patient 
from django.conf import settings 
from django.utils import timezone
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.fields import GenericRelation
from base.models import ArchivableModel, NotArchivedManager

class Department(models.Model):
    name = models.CharField("Наименование отделения", max_length=255)
    slug = models.SlugField("Код отделения (slug)", unique=True, blank=True)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Отделение"
        verbose_name_plural = "Отделения"

    def __str__(self):
        return f"{self.slug} - {self.name}" if self.slug else self.name

class PatientDepartmentStatus(ArchivableModel, models.Model):
    """
    Модель для отслеживания статуса пациента в конкретном отделении.
    Используется для управления переводом и принятием пациентов.
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает принятия'),
        ('accepted', 'Принят в отделение'),
        ('discharged', 'Выписан из отделения'),
        ('transferred_out', 'Переведен в другое отделение'),
        ('transfer_cancelled', 'Перевод отменен'),
    ]

    documents = GenericRelation('documents.ClinicalDocument')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='department_statuses', verbose_name="Пациент")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='patients_in_department', verbose_name="Отделение")
    status = models.CharField("Статус в отделении", max_length=20, choices=STATUS_CHOICES, default='pending')
    admission_date = models.DateTimeField("Дата поступления в отделение", auto_now_add=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Принят сотрудником")
    acceptance_date = models.DateTimeField("Дата принятия", null=True, blank=True)
    discharge_date = models.DateTimeField("Дата выписки", null=True, blank=True)
    notes = models.TextField("Заметки", blank=True)

    source_encounter = models.ForeignKey(
        'encounters.Encounter',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='department_transfer_records',
        verbose_name="Случай обращения-источник перевода"
    )
    
    objects = NotArchivedManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Статус пациента в отделении"
        verbose_name_plural = "Статусы пациентов в отделениях"

    def __str__(self):
        return f"{self.patient.full_name} - {self.department.name} ({self.get_status_display()})"
    
    def get_back_url(self):
        """Возвращает URL для возврата к детальному просмотру пациента"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})

    def accept_patient(self, user):
        """
        Метод для принятия пациента в отделение.
        """
        if self.status == 'pending':
            self.status = 'accepted'
            self.accepted_by = user
            self.save()
            return True
        return False

    def discharge_patient(self):
        """
        Метод для выписки пациента из отделения.
        """
        if self.status == 'accepted':
            self.status = 'discharged'
            self.discharge_date = timezone.now()
            self.save()
            return True
        return False
    
    def cancel_transfer(self):
        """
        Отменяет перевод, если статус 'pending' или 'accepted'.
        """
        if self.status in ['pending', 'accepted']:
            self.status = 'transfer_cancelled'
            self.notes = (self.notes + "\n" if self.notes else "") + \
                         f"Перевод отменен в {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            self.save()
            return True
        return False

    def unarchive(self):
        # Не делаем каскадное разархивирование source_encounter, 
        # чтобы избежать рекурсии. Encounter сам управляет разархивированием связанных записей.
        super().unarchive()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)