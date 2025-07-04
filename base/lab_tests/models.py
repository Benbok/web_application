from django.db import models

class LabTestDefinition(models.Model):
    name = models.CharField("Название лабораторного исследования", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Лабораторное исследование (определение)"
        verbose_name_plural = "Лабораторные исследования (определения)"
        ordering = ['name']

    def __str__(self):
        return self.name