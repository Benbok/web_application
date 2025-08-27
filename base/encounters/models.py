from django.db import models
from django.conf import settings
from patients.models import Patient
from django.utils import timezone
# Убираем неиспользуемый импорт
# from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError

from documents.models import ClinicalDocument
from departments.models import PatientDepartmentStatus, Department
from diagnosis.models import Diagnosis
from base.models import ArchivableModel, NotArchivedManager

class EncounterDiagnosis(models.Model):
    """Модель для хранения диагнозов случая обращения"""
    
    DIAGNOSIS_TYPE_CHOICES = [
        ('main', 'Основной диагноз'),
        ('complication', 'Осложнение'),
        ('comorbidity', 'Сопутствующий диагноз'),
    ]
    
    encounter = models.ForeignKey(
        'Encounter',
        on_delete=models.CASCADE,
        related_name='diagnoses',
        verbose_name="Случай обращения"
    )
    diagnosis_type = models.CharField(
        "Тип диагноза",
        max_length=20,
        choices=DIAGNOSIS_TYPE_CHOICES,
        default='main'
    )
    diagnosis = models.ForeignKey(
        'diagnosis.Diagnosis',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Диагноз из справочника",
        related_name="encounter_diagnoses"
    )
    custom_diagnosis = models.TextField(
        "Собственный диагноз",
        blank=True,
        help_text="Введите диагноз в свободной форме"
    )
    description = models.TextField(
        "Описание",
        blank=True,
        help_text="Дополнительное описание диагноза"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Диагноз случая"
        verbose_name_plural = "Диагнозы случая"
        ordering = ['diagnosis_type', 'created_at']
        # Убираем unique_together, так как для осложнений и сопутствующих диагнозов
        # нужно разрешить множественные записи
    
    def __str__(self):
        if self.diagnosis:
            return f"{self.get_diagnosis_type_display()}: {self.diagnosis}"
        elif self.custom_diagnosis:
            return f"{self.get_diagnosis_type_display()}: {self.custom_diagnosis}"
        return f"{self.get_diagnosis_type_display()}"
    
    def clean(self):
        """Проверяем, что либо выбран диагноз из справочника, либо введен собственный"""

        
        if not self.diagnosis and not self.custom_diagnosis:
            raise ValidationError("Необходимо выбрать диагноз из справочника или ввести собственный диагноз")
        
        if self.diagnosis and self.custom_diagnosis:
            raise ValidationError("Нельзя одновременно выбирать диагноз из справочника и вводить собственный")
        
        # Проверяем уникальность для основного диагноза
        if self.diagnosis_type == 'main' and hasattr(self, 'encounter') and self.encounter:
            # Для основного диагноза проверяем, что нет дубликатов
            existing_main = EncounterDiagnosis.objects.filter(
                encounter=self.encounter,
                diagnosis_type='main'
            ).exclude(pk=self.pk)
            
            if existing_main.exists():
                raise ValidationError("Основной диагноз уже установлен для этого случая")
    
    def get_display_name(self):
        """Возвращает отображаемое название диагноза"""
        if self.diagnosis:
            return str(self.diagnosis)
        return self.custom_diagnosis


class Encounter(ArchivableModel, models.Model):
    OUTCOME_CHOICES = [
        ('consultation_end', 'Консультация'),
        ('transferred', 'Перевод в отделение'),
    ]

    outcome = models.CharField("Исход", max_length=30, choices=OUTCOME_CHOICES, null=True, blank=True)
    transfer_to_department = models.ForeignKey(
        'departments.Department',
        verbose_name="Переведён в отделение",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferred_encounters"
    )
    # Убираем GenericRelation, используем только прямую связь
    # documents = GenericRelation(ClinicalDocument)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # Старое поле диагноза (оставляем для обратной совместимости)
    diagnosis = models.ForeignKey(
        'diagnosis.Diagnosis', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Диагноз (устаревшее)",
        related_name="encounters"
    )
    date_start = models.DateTimeField("Дата начала")
    date_end = models.DateTimeField("Дата завершения", null=True, blank=True)
    is_active = models.BooleanField("Активен", default=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NotArchivedManager()
    all_objects = models.Manager()
    
    class OptimizedManager(models.Manager):
        """Менеджер с оптимизированными запросами для избежания N+1 проблем"""
        
        def get_queryset(self):
            return super().get_queryset().select_related(
                'patient',
                'doctor',
                'transfer_to_department'
            ).prefetch_related(
                'clinical_documents',  # Используем только прямую связь
                'diagnoses__diagnosis',
                'department_transfer_records'
            )
    
    optimized_objects = OptimizedManager()

    class Meta:
        verbose_name = "Случай обращения"
        verbose_name_plural = "Случаи обращений"
        indexes = [
            models.Index(fields=['is_active']),
        ]
        ordering = ["is_active", "-date_start"]

    def __str__(self):
        if self.outcome:
            return f"Случай от {self.date_start.strftime('%d.%m.%Y')} — {self.patient.full_name} ({self.get_outcome_display()})"
        return f"Случай от {self.date_start.strftime('%d.%m.%Y')} — {self.patient.full_name}"
    

        
    def close_encounter(self, outcome, transfer_department=None):
        """
        Метод для закрытия случая обращения.
        Позволяет инкапсулировать логику закрытия.
        """
        if not self.has_documents():
            raise ValueError("Необходимо прикрепить хотя бы один документ для закрытия случая.")

        if self.is_active:
            # Если есть связанный appointment — берем дату окончания из него
            if hasattr(self, 'appointment') and self.appointment and self.appointment.end:
                self.date_end = self.appointment.end
            else:
                self.date_end = timezone.now()
            self.outcome = outcome
            if outcome == 'transferred' and transfer_department:
                self.transfer_to_department = transfer_department
            self.save()
            return True
        return False
    
    def reopen_encounter(self):
        """
        Метод для возврата случая обращения в активное состояние.
        При этом отменяется связанная запись PatientDepartmentStatus, если она была создана переводом.
        """
        if not self.is_active:
            # Если случай был закрыт как "переведен"
            if self.outcome == 'transferred' and self.transfer_to_department:
                # Находим последнюю запись PatientDepartmentStatus, которая была создана этим Encounter
                # Фильтруем по patient, department и source_encounter, чтобы быть максимально точными
                patient_dept_status = PatientDepartmentStatus.objects.filter(
                    patient=self.patient,
                    department=self.transfer_to_department,
                    source_encounter=self
                ).order_by('-admission_date').first() # Берем последнюю, если их несколько по какой-то причине

                if patient_dept_status:
                    if patient_dept_status.cancel_transfer():
                        print(f"Записть перевода {patient_dept_status.pk} для пациента {self.patient.full_name} в {self.transfer_to_department.name} была отменена.")
                    else:
                        print(f"Could not cancel transfer record {patient_dept_status.pk} (status {patient_dept_status.status}).")
                else:
                    print(f"No PatientDepartmentStatus found for transfer of encounter {self.pk}.")

            self.date_end = None
            self.outcome = None
            self.transfer_to_department = None
            self.is_active = True
            self.save()
            # Синхронизация с AppointmentEvent
            if hasattr(self, 'appointment') and self.appointment:
                from appointments.models import AppointmentStatus
                if self.appointment.status != AppointmentStatus.SCHEDULED:
                    self.appointment.status = AppointmentStatus.SCHEDULED
                    self.appointment.save(update_fields=['status'])
            return True
        return False 
    
    def clean(self):
        if self.date_end and self.date_start and self.date_end < self.date_start:
            raise ValidationError("Дата завершения не может быть раньше даты начала.")

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем дату начала для новых случаев
        if not self.pk and not self.date_start:
            self.date_start = timezone.now()
        
        if self.date_end and self.outcome:
            self.is_active = False
        else:
            self.is_active = True
        super().save(*args, **kwargs)
        # Синхронизация статуса AppointmentEvent
        if hasattr(self, 'appointment'):
            from appointments.models import AppointmentStatus
            appointment = getattr(self, 'appointment', None)
            if appointment:
                if not self.is_active and appointment.status != AppointmentStatus.COMPLETED:
                    appointment.status = AppointmentStatus.COMPLETED
                    appointment.save(update_fields=['status'])

    def archive(self):
        # Обнуляем ссылку на Encounter в AppointmentEvent, если есть
        appointment = getattr(self, 'appointment', None)
        if appointment is not None:
            appointment.encounter = None
            appointment.save(update_fields=['encounter'])

        # Архивируем все связанные PatientDepartmentStatus
        for dept_status in self.department_transfer_records.all():
            if not getattr(dept_status, 'is_archived', False):
                dept_status.archive()

        super().archive()

    def unarchive(self):
        # Восстанавливаем связанные AppointmentEvent
        appointment = getattr(self, 'appointment', None)
        if appointment is not None and getattr(appointment, 'is_archived', False):
            appointment.unarchive()
        # Восстанавливаем все связанные PatientDepartmentStatus (включая архивированные)
        from departments.models import PatientDepartmentStatus
        for dept_status in PatientDepartmentStatus.all_objects.filter(source_encounter=self):
            if getattr(dept_status, 'is_archived', False):
                dept_status.unarchive()
        super().unarchive()
    
    # Методы для работы с диагнозами
    def get_main_diagnosis(self):
        """Возвращает основной диагноз"""
        return self.diagnoses.filter(diagnosis_type='main').first()
    

    
    def add_diagnosis(self, diagnosis_type, diagnosis=None, custom_diagnosis='', description=''):
        """Добавляет диагноз к случаю"""
        if diagnosis_type == 'main':
            # Удаляем существующий основной диагноз
            self.diagnoses.filter(diagnosis_type='main').delete()
        
        return self.diagnoses.create(
            diagnosis_type=diagnosis_type,
            diagnosis=diagnosis,
            custom_diagnosis=custom_diagnosis,
            description=description
        )
    
    def get_main_diagnosis_for_recommendations(self):
        """Получает основной диагноз для рекомендаций по лечению"""
        main_diagnosis = self.get_main_diagnosis()
        if main_diagnosis and main_diagnosis.diagnosis:
            return main_diagnosis.diagnosis
        return None
