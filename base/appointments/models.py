from django.db import models
from datetime import timedelta


class Appointment(models.Model):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('profiles.DoctorProfile', on_delete=models.CASCADE, related_name='appointments')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['start_time']
        unique_together = ('doctor', 'start_time')

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = self.start_time + timedelta(minutes=30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} → {self.doctor} @ {self.start_time}"