from django.db import models
from django.conf import settings
from patients.models import Patient
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation

from documents.models import ClinicalDocument
from departments.models import PatientDepartmentStatus

class Encounter(models.Model):
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
    documents = GenericRelation(ClinicalDocument)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_start = models.DateTimeField("Дата начала")
    date_end = models.DateTimeField("Дата завершения", null=True, blank=True)
    is_active = models.BooleanField("Активен", default=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Случай обращения"
        verbose_name_plural = "Случаи обращений"
        ordering = ["is_active", "-date_start"]

    def __str__(self):
        if self.outcome:
            return f"Случай от {self.date_start.strftime('%d.%m.%Y')} — {self.patient.full_name} ({self.get_outcome_display()})"
        return f"Случай от {self.date_start.strftime('%d.%m.%Y')} — {self.patient.full_name}"

    def save(self, *args, **kwargs):
        if self.date_end and self.outcome:
            self.is_active = False
        else:
            self.is_active = True
        super().save(*args, **kwargs)
        
    def close_encounter(self, outcome, transfer_department=None):
        """
        Метод для закрытия случая обращения.
        Позволяет инкапсулировать логику закрытия.
        """
        if not self.documents.exists():
            raise ValueError("Необходимо прикрепить хотя бы один документ для закрытия случая.")

        if self.is_active:
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
            return True
        return False 
    
    def delete(self, *args, **kwargs):
        """
        Переопределяем метод delete() для каскадного удаления связанных ClinicalDocument.
        А также, опционально, для отмены связанных PatientDepartmentStatus.
        """
        # Удаляем все связанные документы
        for document in self.documents.all():
            document.delete()

        # Отменяем связанные PatientDepartmentStatus (если их не удаляем полностью)
        # Если вы хотите *удалять* PatientDepartmentStatus при удалении Encounter,
        # то вместо cancel_transfer() используйте patient_status.delete().
        # Но "отмена" обычно предпочтительнее "удаления" для истории.
        for patient_status in self.department_transfer_records.all(): # Используем related_name 'department_transfer_records'
            if patient_status.status not in ['discharged', 'transferred_out']: # Не отменяем уже завершенные статусы
                patient_status.cancel_transfer()


        super().delete(*args, **kwargs)