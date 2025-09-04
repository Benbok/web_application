from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

class ScheduledAppointment(models.Model):
    """
    Запланированное клиническое событие - тактический уровень управления
    """
    
    # Связь с назначением через GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    assignment = GenericForeignKey('content_type', 'object_id')
    
    # Связь с пациентом - ОБЯЗАТЕЛЬНОЕ поле
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        verbose_name=_('Пациент'),
        related_name='scheduled_appointments'
    )
    
    # Связь с отделением, где было создано назначение
    created_department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        verbose_name=_('Отделение создания'),
        related_name='created_appointments',
        help_text=_('Отделение, где было создано это назначение')
    )
    
    # Связь со случаем поступления
    encounter = models.ForeignKey(
        'encounters.Encounter',
        on_delete=models.CASCADE,
        verbose_name=_('Случай поступления'),
        related_name='scheduled_appointments',
        null=True,
        blank=True
    )
    
    # Временные параметры
    scheduled_date = models.DateField(_('Запланированная дата'))
    scheduled_time = models.TimeField(_('Запланированное время'), null=True, blank=True)
    
    # Статус выполнения
    EXECUTION_STATUS_CHOICES = [
        ('scheduled', _('Запланировано')),
        ('completed', _('Выполнено')),
        ('skipped', _('Пропущено')),
        ('partial', _('Введено не полностью')),
        ('canceled', _('Отменено')),
        ('rejected', _('Забраковано')),
    ]
    execution_status = models.CharField(
        _('Статус выполнения'), 
        max_length=20, 
        choices=EXECUTION_STATUS_CHOICES, 
        default='scheduled'
    )
    
    # Информация о выполнении
    executed_at = models.DateTimeField(_('Время выполнения'), null=True, blank=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_('Выполнил')
    )
    execution_notes = models.TextField(_('Примечания к выполнению'), blank=True)
    
    # Информация об отклонении
    rejection_reason = models.TextField(_('Причина брака'), blank=True)
    rejection_date = models.DateTimeField(_('Дата брака'), null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_('Забраковал'), 
        related_name='rejected_appointments'
    )
    
    # Информация о частичном выполнении
    partial_reason = models.TextField(_('Причина неполного выполнения'), blank=True)
    partial_amount = models.CharField(_('Выполненное количество'), max_length=100, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Запланированное клиническое событие')
        verbose_name_plural = _('Запланированные клинические события')
        ordering = ['-scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['scheduled_date', 'execution_status']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['execution_status', 'scheduled_date']),
            models.Index(fields=['patient', 'scheduled_date']),
            models.Index(fields=['created_department', 'scheduled_date']),
            models.Index(fields=['encounter', 'scheduled_date']),
        ]
        unique_together = ['content_type', 'object_id', 'scheduled_date', 'scheduled_time']
    
    def __str__(self):
        assignment_name = getattr(self.assignment, 'treatment_name', str(self.assignment))
        return f"{assignment_name} - {self.scheduled_date} {self.scheduled_time or ''}"
    
    @property
    def is_overdue(self):
        """Проверяет, просрочено ли назначение"""
        today = timezone.now().date()
        return (self.scheduled_date < today and 
                self.execution_status in ['scheduled', 'partial'])
    
    @property
    def is_due_today(self):
        """Проверяет, назначено ли на сегодня"""
        today = timezone.now().date()
        return self.scheduled_date == today
    
    @property
    def can_be_executed(self):
        """Можно ли выполнить назначение"""
        return self.execution_status in ['scheduled', 'partial']
    
    @property
    def can_be_rejected(self):
        """Можно ли отклонить назначение"""
        return self.execution_status in ['scheduled', 'partial', 'completed']
    
    def can_be_edited_by_user(self, user):
        """Проверяет, может ли пользователь редактировать назначение"""
        if user.is_superuser:
            return True
        
        # Пользователь может редактировать только назначения из своего отделения
        try:
            user_department = user.department
            return user_department == self.created_department
        except:
            return False
    
    def mark_as_completed(self, user, notes=''):
        """Отмечает назначение как выполненное"""
        self.execution_status = 'completed'
        self.executed_at = timezone.now()
        self.executed_by = user
        self.execution_notes = notes
        self.save()
    
    def mark_as_rejected(self, user, reason=''):
        """Отмечает назначение как отклоненное"""
        self.execution_status = 'rejected'
        self.rejection_reason = reason
        self.rejection_date = timezone.now()
        self.rejected_by = user
        self.save()
    
    def mark_as_skipped(self, user, reason=''):
        """Отмечает назначение как пропущенное"""
        self.execution_status = 'skipped'
        self.executed_by = user
        self.execution_notes = reason
        self.save()
    
    def mark_as_partial(self, user, reason='', partial_amount=''):
        """Отмечает назначение как частично выполненное"""
        self.execution_status = 'partial'
        self.executed_by = user
        self.execution_notes = reason
        self.partial_reason = reason
        self.partial_amount = partial_amount
        self.save()
    
    def get_assignment_info(self):
        """Получает информацию о связанном назначении"""
        # Сначала пробуем через GenericForeignKey
        assignment = self.assignment
        
        # Если GenericForeignKey не работает, получаем объект напрямую
        if assignment is None and self.content_type and self.object_id:
            try:
                model_class = self.content_type.model_class()
                assignment = model_class.objects.get(id=self.object_id)
            except Exception as e:
                assignment = None
        
        if assignment is None:
            return {
                'type': 'unknown', 
                'name': 'Назначение не найдено', 
                'patient': self.patient,
                'department': self.created_department
            }
        
        # Проверяем тип назначения и получаем нужную информацию
        if hasattr(assignment, 'medication'):
            # Это TreatmentMedication - показываем только название препарата
            return {
                'type': 'treatment', 
                'name': assignment.medication.name, 
                'patient': self.patient,
                'department': self.created_department
            }
        elif hasattr(assignment, 'lab_test'):
            # Это LabTestResult - показываем только название исследования
            return {
                'type': 'lab_test', 
                'name': assignment.lab_test.name if assignment.lab_test else 'Лабораторное исследование', 
                'patient': self.patient,
                'department': self.created_department
            }
        elif hasattr(assignment, 'instrumental_procedure'):
            # Это InstrumentalProcedureResult - показываем только название процедуры
            return {
                'type': 'procedure', 
                'name': assignment.instrumental_procedure.name if assignment.instrumental_procedure else 'Процедура', 
                'patient': self.patient,
                'department': self.created_department
            }
        elif hasattr(assignment, 'text'):
            # Это рекомендация - показываем текст рекомендации
            return {
                'type': 'recommendation', 
                'name': assignment.text, 
                'patient': self.patient,
                'department': self.created_department
            }
        else:
            # Используем __str__ метод объекта
            return {
                'type': 'unknown', 
                'name': str(assignment), 
                'patient': self.patient,
                'department': self.created_department
            }