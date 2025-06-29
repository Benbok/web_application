from django.db import models
from django.conf import settings
from patients.models import Patient
from django.contrib.contenttypes.fields import GenericRelation
from documents.models import ClinicalDocument

class Encounter(models.Model):
    OUTCOME_CHOICES = [
        ('discharged', 'Выписан'),
        ('transferred', 'Переведён'),
        ('consultation_end', 'Завершена консультация'),
    ]

    outcome = models.CharField("Исход", max_length=30, choices=OUTCOME_CHOICES, null=True, blank=True)
    # transfer_to_department = models.ForeignKey(
    #     'departments.Department',
    #     verbose_name="Переведён в отделение",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="transferred_encounters"
    # )
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
        ordering = ["-date_start"]

    def __str__(self):
        return f"{self.get_type_display()} от {self.date_start.strftime('%d.%m.%Y')} — {self.patient.full_name}"

    def save(self, *args, **kwargs):
        if self.date_end:
            self.is_active = False
        else:
            self.is_active = True
        super().save(*args, **kwargs)