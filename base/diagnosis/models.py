from django.db import models


class Diagnosis(models.Model):
    code = models.CharField("Код диагноза (МКБ-10)", max_length=20, unique=True)
    name = models.CharField("Наименование диагноза", max_length=255)

    class Meta:
        verbose_name = "Диагноз"
        verbose_name_plural = "Диагнозы"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}" 