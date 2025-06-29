from django.db import models
from django.conf import settings
from patients.models import Patient

class Encounter(models.Model):
    ENCOUNTER_TYPE_CHOICES = [
        ('consultation', 'Консультация'),
        ('admission', 'Поступление'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField("Тип случая", max_length=20, choices=ENCOUNTER_TYPE_CHOICES)
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