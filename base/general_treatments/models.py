from django.db import models

class GeneralTreatmentDefinition(models.Model):
    name = models.CharField("Название общего назначения", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Общее назначение (определение)"
        verbose_name_plural = "Общие назначения (определения)"
        ordering = ['name']

    def __str__(self):
        return self.name