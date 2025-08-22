from django.db import models
from django.conf import settings
from django.utils import timezone

class LabTestDefinition(models.Model):
    name = models.CharField("Название лабораторного исследования", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True, null=True)
    schema = models.JSONField("Схема полей результата (JSON)", help_text="Описывает поля, их типы и метки", blank=True, null=True)

    class Meta:
        verbose_name = "Лабораторное исследование (определение)"
        verbose_name_plural = "Лабораторные исследования (определения)"
        ordering = ['name']

    def __str__(self):
        return self.name

class LabTestResult(models.Model):
    # Убираем зависимость от treatment_assignments
    # lab_test_assignment = models.ForeignKey(
    #     'treatment_assignments.LabTestAssignment',
    #     on_delete=models.CASCADE,
    #     related_name='results',
    #     verbose_name="Назначение лабораторного исследования"
    # )
    
    # Добавляем прямые связи
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        verbose_name="Пациент",
        related_name='lab_test_results'
    )
    
    examination_plan = models.ForeignKey(
        'examination_management.ExaminationPlan',
        on_delete=models.CASCADE,
        verbose_name="План обследования",
        related_name='lab_test_results',
        null=True,
        blank=True
    )
    
    procedure_definition = models.ForeignKey(
        LabTestDefinition,
        on_delete=models.PROTECT,
        verbose_name="Тип исследования",
        related_name='results'
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Автор")
    datetime_result = models.DateTimeField("Дата результата", default=timezone.now)
    data = models.JSONField("Данные результата", default=dict)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Результат лабораторного исследования"
        verbose_name_plural = "Результаты лабораторных исследований"
        ordering = ["-datetime_result"]

    def __str__(self):
        return f"Результат {self.procedure_definition.name} для {self.patient} от {self.datetime_result.strftime('%d.%m.%Y')}"
