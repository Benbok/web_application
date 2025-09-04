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
from base.models import ArchivableModel
from base.services import ArchiveManager



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
    
    def get_owner(self):
        """Возвращает объект-владелец плана обследования"""
        if self.patient_department_status:
            return self.patient_department_status
        elif self.encounter:
            return self.encounter
        elif self.owner:
            return self.owner
        return None
    
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


class ExaminationPlan(ArchivableModel, BaseExaminationPlan):
    """План обследования с поддержкой двух типов связей и архивирования"""
    
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
        Получить статус лабораторного исследования через сервис
        """
        from .services import ExaminationStatusService
        return ExaminationStatusService.get_assignment_status(examination_lab_test)
    
    def get_instrumental_procedure_status(self, examination_instrumental):
        """
        Получить статус инструментального исследования через сервис
        """
        from .services import ExaminationStatusService
        return ExaminationStatusService.get_assignment_status(examination_instrumental)
    
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
    
    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании ExaminationPlan"""
        # Архивируем связанные лабораторные исследования
        for lab_test in self.lab_tests.all():
            if not lab_test.is_archived:
                if hasattr(lab_test, 'archive'):
                    lab_test.archive(user=user, reason=f"Архивирование связанного плана обследования: {reason}")
        
        # Архивируем связанные инструментальные исследования
        for instrumental in self.instrumental_procedures.all():
            if not instrumental.is_archived:
                if hasattr(instrumental, 'archive'):
                    instrumental.archive(user=user, reason=f"Архивирование связанного плана обследования: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении ExaminationPlan"""
        # Восстанавливаем связанные лабораторные исследования
        for lab_test in self.lab_tests.all():
            if lab_test.is_archived:
                if hasattr(lab_test, 'restore'):
                    lab_test.restore(user=user)
        
        # Восстанавливаем связанные инструментальные исследования
        for instrumental in self.instrumental_procedures.all():
            if instrumental.is_archived:
                if hasattr(instrumental, 'restore'):
                    instrumental.restore(user=user)


from base.models import ArchivableModel
from base.services import ArchiveManager

class ExaminationLabTest(ArchivableModel, models.Model):
    """
    Лабораторное исследование в плане обследования с поддержкой архивирования
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
    scheduled_time = models.TimeField(_('Время выполнения'), null=True, blank=True, help_text=_('Время выполнения исследования'))
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    # Статус назначения
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
        related_name='cancelled_lab_tests'
    )
    cancellation_reason = models.TextField(_('Причина отмены'), blank=True)
    
    # Используем стандартное архивирование через ArchivableModel
    
    class Meta:
        verbose_name = _('Лабораторное исследование в плане')
        verbose_name_plural = _('Лабораторные исследования в плане')
        ordering = ['-created_at']
    
    def __str__(self):
        time_str = f" ({self.scheduled_time.strftime('%H:%M')})" if self.scheduled_time else ""
        return f"{self.lab_test.name} в плане {self.examination_plan.name}{time_str} [ID: {self.pk}]"
    
    def get_absolute_url(self):
        return reverse('examination_management:lab_test_detail', kwargs={'pk': self.pk})
    
    def get_lab_test_name(self):
        """Получить название лабораторного исследования"""
        return self.lab_test.name
    
    def get_scheduled_datetime(self):
        """
        Возвращает дату и время начала расписания
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self)
            appointment = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.pk
            ).order_by('-scheduled_date', 'scheduled_time').first()
            
            if appointment:
                from django.utils import timezone
                return timezone.make_aware(
                    timezone.datetime.combine(appointment.scheduled_date, appointment.scheduled_time or timezone.now().time())
                )
            
            return None
            
        except Exception:
            return None
    
    def can_be_cancelled(self):
        """
        Проверяет, можно ли отменить назначение
        Нельзя отменить, если есть подписанное заключение
        """
        try:
            from lab_tests.models import LabTestResult
            from document_signatures.models import DocumentSignature
            from django.contrib.contenttypes.models import ContentType
            
            # Проверяем, есть ли заполненный результат
            result = LabTestResult.objects.filter(
                examination_plan=self.examination_plan,
                procedure_definition=self.lab_test,
                is_completed=True
            ).first()
            
            if result:
                # Проверяем, есть ли подпись
                signature = DocumentSignature.objects.filter(
                    content_type=ContentType.objects.get_for_model(LabTestResult),
                    object_id=result.pk,
                    is_signed=True
                ).first()
                
                if signature:
                    return False, "Есть подписанное заключение. Сначала удалите заключение в разделе лабораторных исследований."
            
            return True, None
            
        except Exception:
            return True, None
    
    def cancel(self, reason="", cancelled_by=None):
        """
        Отменяет назначение, архивирует его и синхронизирует с lab_tests
        """
        from django.utils import timezone
        
        can_cancel, error_message = self.can_be_cancelled()
        if not can_cancel:
            raise ValidationError(error_message)
        
        # Устанавливаем статус отмены
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        
        # Архивируем запись
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = cancelled_by
        self.archive_reason = f"Отменено: {reason}"
        
        self.save(update_fields=[
            'status', 'cancelled_at', 'cancelled_by', 'cancellation_reason',
            'is_archived', 'archived_at', 'archived_by', 'archive_reason'
        ])
        
        # Синхронизируем с clinical_scheduling
        self._sync_with_clinical_scheduling()
        
        # Синхронизируем с lab_tests
        self._sync_with_lab_tests()
    
    def _sync_with_lab_tests(self):
        """
        Синхронизирует отмену с lab_tests
        """
        try:
            from lab_tests.models import LabTestResult
            
            # Находим соответствующий результат лабораторного исследования
            lab_test_result = LabTestResult.objects.filter(
                examination_plan=self.examination_plan,
                procedure_definition=self.lab_test
            ).first()
            
            if lab_test_result and lab_test_result.status != 'cancelled':
                # Отменяем результат исследования
                lab_test_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {self.cancellation_reason}",
                    cancelled_by=self.cancelled_by
                )
                print(f"Отменен LabTestResult {lab_test_result.pk} для ExaminationLabTest {self.pk}")
                
        except Exception as e:
            print(f"Ошибка синхронизации с lab_tests: {e}")
    
    def _sync_with_clinical_scheduling(self):
        """
        Синхронизирует статус с clinical_scheduling
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self)
            appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.pk
            )
            
            for appointment in appointments:
                if self.status == 'cancelled':
                    appointment.execution_status = 'canceled'
                elif self.status == 'completed':
                    appointment.execution_status = 'completed'
                elif self.status == 'paused':
                    appointment.execution_status = 'skipped'
                elif self.status == 'active':
                    appointment.execution_status = 'scheduled'
                
                appointment.save(update_fields=['execution_status'])
                
        except Exception as e:
            print(f"Ошибка синхронизации с clinical_scheduling: {e}")


class ExaminationInstrumental(ArchivableModel, models.Model):
    """
    Инструментальное исследование в плане обследования с поддержкой архивирования
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
    
    # Статус назначения
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
        related_name='cancelled_instrumentals'
    )
    cancellation_reason = models.TextField(_('Причина отмены'), blank=True)
    
    # Используем стандартное архивирование через ArchivableModel
    
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
    
    def get_scheduled_datetime(self):
        """
        Возвращает дату и время начала расписания
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self)
            appointment = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.pk
            ).order_by('-scheduled_date', 'scheduled_time').first()
            
            if appointment:
                from django.utils import timezone
                return timezone.make_aware(
                    timezone.datetime.combine(appointment.scheduled_date, appointment.scheduled_time or timezone.now().time())
                )
            
            return None
            
        except Exception:
            return None
    
    def can_be_cancelled(self):
        """
        Проверяет, можно ли отменить назначение
        Нельзя отменить, если есть подписанное заключение
        """
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            from document_signatures.models import DocumentSignature
            from django.contrib.contenttypes.models import ContentType
            
            # Проверяем, есть ли заполненный результат
            result = InstrumentalProcedureResult.objects.filter(
                examination_plan=self.examination_plan,
                procedure_definition=self.instrumental_procedure,
                is_completed=True
            ).first()
            
            if result:
                # Проверяем, есть ли подпись
                signature = DocumentSignature.objects.filter(
                    content_type=ContentType.objects.get_for_model(InstrumentalProcedureResult),
                    object_id=result.pk,
                    is_signed=True
                ).first()
                
                if signature:
                    return False, "Есть подписанное заключение. Сначала удалите заключение в разделе инструментальных исследований."
            
            return True, None
            
        except Exception:
            return True, None
    
    def cancel(self, reason="", cancelled_by=None):
        """
        Отменяет назначение, архивирует его и синхронизирует с instrumental_procedures
        """
        from django.utils import timezone
        
        can_cancel, error_message = self.can_be_cancelled()
        if not can_cancel:
            raise ValidationError(error_message)
        
        # Устанавливаем статус отмены
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        
        # Архивируем запись
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = cancelled_by
        self.archive_reason = f"Отменено: {reason}"
        
        self.save(update_fields=[
            'status', 'cancelled_at', 'cancelled_by', 'cancellation_reason',
            'is_archived', 'archived_at', 'archived_by', 'archive_reason'
        ])
        
        # Синхронизируем с clinical_scheduling
        self._sync_with_clinical_scheduling()
        
        # Синхронизируем с instrumental_procedures
        self._sync_with_instrumental_procedures()
    
    def _sync_with_instrumental_procedures(self):
        """
        Синхронизирует отмену с instrumental_procedures
        """
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            
            # Находим соответствующий результат инструментального исследования
            instrumental_result = InstrumentalProcedureResult.objects.filter(
                examination_plan=self.examination_plan,
                procedure_definition=self.instrumental_procedure
            ).first()
            
            if instrumental_result and instrumental_result.status != 'cancelled':
                # Отменяем результат исследования
                instrumental_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {self.cancellation_reason}",
                    cancelled_by=self.cancelled_by
                )
                print(f"Отменен InstrumentalProcedureResult {instrumental_result.pk} для ExaminationInstrumental {self.pk}")
                
        except Exception as e:
            print(f"Ошибка синхронизации с instrumental_procedures: {e}")
    
    def _sync_with_clinical_scheduling(self):
        """
        Синхронизирует статус с clinical_scheduling
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self)
            appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.pk
            )
            
            for appointment in appointments:
                if self.status == 'cancelled':
                    appointment.execution_status = 'canceled'
                elif self.status == 'completed':
                    appointment.execution_status = 'completed'
                elif self.status == 'paused':
                    appointment.execution_status = 'skipped'
                elif self.status == 'active':
                    appointment.execution_status = 'scheduled'
                
                appointment.save(update_fields=['execution_status'])
                
        except Exception as e:
            print(f"Ошибка синхронизации с clinical_scheduling: {e}")

# ============================================================================
# СИГНАЛЫ УДАЛЕНЫ - больше не нужны, так как treatment_assignments удалено
# ============================================================================
