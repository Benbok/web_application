from django.db import models

class Patient(models.Model):
    full_name = models.CharField(verbose_name='ФИО', max_length=255)
    date_of_birth = models.DateField(verbose_name='Дата рождения')

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Пациент'
        verbose_name_plural = 'Пациенты'