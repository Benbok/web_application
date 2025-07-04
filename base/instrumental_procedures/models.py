from django.db import models

class InstrumentalProcedureDefinition(models.Model):
    name = models.CharField("Название инструментального исследования", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Инструментальное исследование (определение)"
        verbose_name_plural = "Инструментальные исследования (определения)"
        ordering = ['name']

    def __str__(self):
        return self.name