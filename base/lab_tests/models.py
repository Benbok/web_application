from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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
    
    examination_lab_test = models.ForeignKey(
        'examination_management.ExaminationLabTest',
        on_delete=models.CASCADE,
        verbose_name="Назначение лабораторного исследования",
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
    is_completed = models.BooleanField("Заполнено", default=False, help_text="Заполнены ли данные результата")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    # Статус назначения для синхронизации с examination_management
    STATUS_CHOICES = [
        ('active', _('Активно')),
        ('cancelled', _('Отменено')),
        ('completed', _('Завершено')),
        ('paused', _('Приостановлено')),
    ]
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    cancelled_at = models.DateTimeField(_('Отменено'), null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Отменено пользователем'),
        related_name='cancelled_lab_test_results'
    )
    cancellation_reason = models.TextField(_('Причина отмены'), blank=True)

    class Meta:
        verbose_name = "Результат лабораторного исследования"
        verbose_name_plural = "Результаты лабораторных исследований"
        ordering = ["-datetime_result"]

    def __str__(self):
        return f"Результат {self.procedure_definition.name} для {self.patient} от {self.datetime_result.strftime('%d.%m.%Y')}"
    
    def get_assignment_schedule_data(self):
        """
        Получает данные расписания из связанного назначения
        """
        if self.examination_lab_test:
            from examination_management.services import ExaminationStatusService
            return ExaminationStatusService.get_schedule_data(self.examination_lab_test)
        return None

    def cancel(self, reason="", cancelled_by=None):
        """
        Отменяет результат исследования
        """
        from django.utils import timezone
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason'])
