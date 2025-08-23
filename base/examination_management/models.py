from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from encounters.models import Encounter
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition
from treatment_management.mixins import SoftDeleteMixin


class BaseExaminationPlan(models.Model):
    """Базовый класс для планов обследования с поддержкой двух типов связей"""
    
    # Прямые связи для departments
    patient_department_status = models.ForeignKey(
        'departments.PatientDepartmentStatus',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='examination_plans',
        verbose_name=_('Статус пациента в отделении')
    )
    
    # Прямая связь для encounters
    encounter = models.ForeignKey(
        'encounters.Encounter',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='examination_plans',
        verbose_name=_('Случай обращения')
    )
    
    # GenericForeignKey для обратной совместимости и гибкости
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey('content_type', 'object_id')
    
    # Общие поля
    name = models.CharField(_('Название плана'), max_length=255)
    description = models.TextField(_('Описание'), blank=True)
    priority = models.CharField(
        _('Приоритет'), 
        max_length=20, 
        choices=[
            ('normal', _('Обычный')),
            ('urgent', _('Срочный')),
            ('emergency', _('Экстренный')),
        ], 
        default='normal'
    )
    created_at = models.DateTimeField(_('Создан'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлен'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('Создатель плана')
    )
    
    class Meta:
        abstract = True
        constraints = [
            # Обеспечиваем, что заполнен только один тип связи
            models.CheckConstraint(
                check=(
                    models.Q(patient_department_status__isnull=False, encounter__isnull=True, content_type__isnull=True) |
                    models.Q(patient_department_status__isnull=True, encounter__isnull=False, content_type__isnull=True) |
                    models.Q(patient_department_status__isnull=True, encounter__isnull=True, content_type__isnull=False)
                ),
                name='single_owner_constraint'
            )
        ]
    
    def clean(self):
        """Проверяем, что указан только один тип владельца"""
        owners = [
            bool(self.patient_department_status),
            bool(self.encounter),
            bool(self.owner)
        ]
        if sum(owners) != 1:
            raise ValidationError("Должен быть указан ровно один тип владельца")
    
    def get_owner_display(self):
        """Возвращает читаемое представление владельца"""
        if self.patient_department_status:
            return f"Отделение: {self.patient_department_status.department.name}"
        elif self.encounter:
            return f"Случай: {self.encounter.patient.full_name}"
        elif self.owner:
            if hasattr(self.owner, 'get_display_name'):
                return self.owner.get_display_name()
            return str(self.owner)
        return "Неизвестно"
    
    def get_owner_model_name(self):
        """Возвращает имя модели владельца для использования в шаблонах"""
        if self.patient_department_status:
            return 'patientdepartmentstatus'
        elif self.encounter:
            return 'encounter'
        elif self.owner:
            return self.owner._meta.model_name
        return 'unknown'
    
    @classmethod
    def get_or_create_main_plan(cls, owner_type, owner_id, owner_model=None):
        """
        Получает или создает основной план обследования для указанного владельца
        
        Args:
            owner_type: 'department', 'encounter', или 'generic'
            owner_id: ID владельца
            owner_model: модель для GenericForeignKey (если owner_type == 'generic')
        """
        if owner_type == 'department':
            from departments.models import PatientDepartmentStatus
            owner = PatientDepartmentStatus.objects.get(pk=owner_id)
            plan, created = cls.objects.get_or_create(
                patient_department_status=owner,
                name="Основной",
                defaults={'description': 'Основной план обследования'}
            )
        elif owner_type == 'encounter':
            from encounters.models import Encounter
            owner = Encounter.objects.get(pk=owner_id)
            plan, created = cls.objects.get_or_create(
                encounter=owner,
                name="Основной",
                defaults={'description': 'Основной план обследования'}
            )
        elif owner_type == 'generic' and owner_model:
            content_type = ContentType.objects.get_for_model(owner_model)
            owner = content_type.model_class().objects.get(pk=owner_id)
            plan, created = cls.objects.get_or_create(
                content_type=content_type,
                object_id=owner_id,
                name="Основной",
                defaults={'description': 'Основной план обследования'}
            )
        else:
            raise ValueError("Неверный тип владельца")
        
        return plan, created


class ExaminationPlan(BaseExaminationPlan, SoftDeleteMixin):
    """План обследования с поддержкой двух типов связей и мягкого удаления"""
    
    class Meta:
        verbose_name = _('План обследования')
        verbose_name_plural = _('Планы обследования')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_department_status', 'created_at']),
            models.Index(fields=['encounter', 'created_at']),
            models.Index(fields=['content_type', 'object_id', 'created_at']),
        ]
    
    def __str__(self):
        owner_info = self.get_owner_display()
        return f"{self.name} ({owner_info})"
    
    def get_absolute_url(self):
        return reverse('examination_management:plan_detail', kwargs={'pk': self.pk})
    
    @property
    def lab_tests(self):
        """Получить все лабораторные исследования в плане"""
        return self.examinationlabtest_set.all()
    
    @property
    def instrumental_procedures(self):
        """Получить все инструментальные исследования в плане"""
        return self.examinationinstrumental_set.all()
    
    def get_lab_test_status(self, examination_lab_test):
        """
        Получить статус лабораторного исследования
        """
        try:
            # Сначала проверяем наличие результатов напрямую
            from lab_tests.models import LabTestResult
            has_results = LabTestResult.objects.filter(
                patient=examination_lab_test.examination_plan.get_patient(),
                procedure_definition=examination_lab_test.lab_test,
                examination_plan=examination_lab_test.examination_plan
            ).exists()
            
            if has_results:
                return {
                    'status': 'completed',
                    'status_display': 'Выполнено',
                    'completed_by': None,  # Можно добавить, если нужно
                    'end_date': None,      # Можно добавить, если нужно
                    'rejection_reason': None,
                    'assignment_id': None,
                    'has_results': True
                }
            
            # Проверяем статус в clinical_scheduling
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(examination_lab_test.__class__)
            scheduled_appointment = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=examination_lab_test.pk
            ).first()
            
            if scheduled_appointment:
                return {
                    'status': scheduled_appointment.execution_status,
                    'status_display': scheduled_appointment.get_execution_status_display(),
                    'completed_by': scheduled_appointment.executed_by,
                    'end_date': scheduled_appointment.executed_at,
                    'rejection_reason': scheduled_appointment.rejection_reason,
                    'assignment_id': scheduled_appointment.pk,
                    'has_results': False
                }
            
            # Если ничего не найдено, возвращаем активный статус
            return {
                'status': 'active',
                'status_display': 'Активно',
                'completed_by': None,
                'end_date': None,
                'rejection_reason': None,
                'assignment_id': None,
                'has_results': False
            }
            
        except Exception as e:
            print(f"Ошибка при получении статуса лабораторного исследования: {e}")
            return {
                'status': 'unknown',
                'status_display': 'Неизвестно',
                'completed_by': None,
                'end_date': None,
                'rejection_reason': None,
                'assignment_id': None,
                'has_results': False
            }
    
    def get_instrumental_procedure_status(self, examination_instrumental):
        """
        Получить статус инструментального исследования
        """
        try:
            # Проверяем наличие результатов напрямую
            from instrumental_procedures.models import InstrumentalProcedureResult
            has_results = InstrumentalProcedureResult.objects.filter(
                patient=examination_instrumental.examination_plan.get_patient(),
                procedure_definition=examination_instrumental.instrumental_procedure,
                examination_plan=examination_instrumental.examination_plan
            ).exists()
            
            if has_results:
                return {
                    'status': 'completed',
                    'status_display': 'Выполнено',
                    'completed_by': None,  # Можно добавить, если нужно
                    'end_date': None,      # Можно добавить, если нужно
                    'rejection_reason': None,
                    'assignment_id': None,
                    'has_results': True
                }
            
            # Проверяем статус в clinical_scheduling
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(examination_instrumental.__class__)
            scheduled_appointment = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=examination_instrumental.pk
            ).first()
            
            if scheduled_appointment:
                return {
                    'status': scheduled_appointment.execution_status,
                    'status_display': scheduled_appointment.get_execution_status_display(),
                    'completed_by': scheduled_appointment.executed_by,
                    'end_date': scheduled_appointment.executed_at,
                    'rejection_reason': scheduled_appointment.rejection_reason,
                    'assignment_id': scheduled_appointment.pk,
                    'has_results': False
                }
            
            # Если ничего не найдено, возвращаем активный статус
            return {
                'status': 'active',
                'status_display': 'Активно',
                'completed_by': None,
                'end_date': None,
                'rejection_reason': None,
                'assignment_id': None,
                'has_results': False
            }
            
        except Exception as e:
            print(f"Ошибка при получении статуса инструментального исследования: {e}")
            return {
                'status': 'unknown',
                'status_display': 'Неизвестно',
                'completed_by': None,
                'end_date': None,
                'rejection_reason': None,
                'assignment_id': None,
                'has_results': False
            }
    
    def get_overall_progress(self):
        """
        Получить общий прогресс выполнения плана обследования
        """
        total_items = 0
        completed_items = 0
        rejected_items = 0
        active_items = 0
        
        # Подсчитываем лабораторные исследования
        for lab_test in self.lab_tests.all():
            total_items += 1
            status_info = self.get_lab_test_status(lab_test)
            if status_info['status'] == 'completed':
                completed_items += 1
            elif status_info['status'] == 'rejected':
                rejected_items += 1
            elif status_info['status'] == 'active':
                active_items += 1
        
        # Подсчитываем инструментальные исследования
        for instrumental in self.instrumental_procedures.all():
            total_items += 1
            status_info = self.get_instrumental_procedure_status(instrumental)
            if status_info['status'] == 'completed':
                completed_items += 1
            elif status_info['status'] == 'rejected':
                rejected_items += 1
            elif status_info['status'] == 'active':
                active_items += 1
        
        if total_items == 0:
            return {
                'total': 0,
                'completed': 0,
                'rejected': 0,
                'active': 0,
                'percentage': 0,
                'status': 'empty'
            }
        
        percentage = (completed_items / total_items) * 100
        
        # Определяем общий статус плана
        if completed_items == total_items:
            status = 'completed'
        elif rejected_items == total_items:
            status = 'rejected'
        elif completed_items > 0 or rejected_items > 0:
            status = 'in_progress'
        else:
            status = 'pending'
        
        return {
            'total': total_items,
            'completed': completed_items,
            'rejected': rejected_items,
            'active': active_items,
            'percentage': round(percentage, 1),
            'status': status
        }
    
    def get_patient(self):
        """
        Получает пациента из владельца плана
        """
        if self.patient_department_status:
            return self.patient_department_status.patient
        elif self.encounter:
            return self.encounter.patient
        elif self.owner:
            if hasattr(self.owner, 'patient'):
                return self.owner.patient
            elif hasattr(self.owner, 'get_patient'):
                return self.owner.get_patient()
        return None
    
    def get_owner_model_name(self):
        """
        Получает имя модели владельца для использования в URL
        """
        if self.patient_department_status:
            return 'patientdepartmentstatus'
        elif self.encounter:
            return 'encounter'
        elif self.owner:
            return self.owner._meta.model_name
        return 'unknown'
    
    def get_owner_id(self):
        """
        Получает ID владельца для использования в URL
        """
        if self.patient_department_status:
            return self.patient_department_status.pk
        elif self.encounter:
            return self.encounter.pk
        elif self.owner:
            return self.owner.pk
        return None


from treatment_management.mixins import SoftDeleteMixin

class ExaminationLabTest(SoftDeleteMixin):
    """
    Лабораторное исследование в плане обследования с поддержкой мягкого удаления
    """
    examination_plan = models.ForeignKey(
        ExaminationPlan, 
        on_delete=models.CASCADE, 
        verbose_name=_('План обследования'),
        related_name='lab_tests'
    )
    lab_test = models.ForeignKey(
        LabTestDefinition, 
        on_delete=models.CASCADE, 
        verbose_name=_('Лабораторное исследование'),
        related_name='examination_lab_tests'
    )
    instructions = models.TextField(_('Особые указания'), blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    # Убираем поле is_active, так как теперь используем status из SoftDeleteMixin
    
    class Meta:
        verbose_name = _('Лабораторное исследование в плане')
        verbose_name_plural = _('Лабораторные исследования в плане')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.lab_test.name} в плане {self.examination_plan.name}"
    
    def get_absolute_url(self):
        return reverse('examination_management:lab_test_detail', kwargs={'pk': self.pk})
    
    def get_lab_test_name(self):
        """Получить название лабораторного исследования"""
        return self.lab_test.name


class ExaminationInstrumental(SoftDeleteMixin):
    """
    Инструментальное исследование в плане обследования с поддержкой мягкого удаления
    """
    examination_plan = models.ForeignKey(
        ExaminationPlan, 
        on_delete=models.CASCADE, 
        verbose_name=_('План обследования'),
        related_name='instrumental_procedures'
    )
    instrumental_procedure = models.ForeignKey(
        InstrumentalProcedureDefinition, 
        on_delete=models.CASCADE, 
        verbose_name=_('Инструментальное исследование'),
        related_name='examination_instrumentals'
    )
    instructions = models.TextField(_('Особые указания'), blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    # Убираем поле is_active, так как теперь используем status из SoftDeleteMixin
    
    class Meta:
        verbose_name = _('Инструментальное исследование в плане')
        verbose_name_plural = _('Инструментальные исследования в плане')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.instrumental_procedure.name} в плане {self.examination_plan.name}"
    
    def get_absolute_url(self):
        return reverse('examination_management:instrumental_detail', kwargs={'pk': self.pk})
    
    def get_procedure_name(self):
        """Получить название процедуры"""
        return self.instrumental_procedure.name

# ============================================================================
# СИГНАЛЫ УДАЛЕНЫ - больше не нужны, так как treatment_assignments удалено
# ============================================================================
