from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from pharmacy.models import Medication
from base.models import ArchivableModel
from base.services import ArchiveManager


class BaseTreatmentPlan(models.Model):
    """Базовый класс для планов лечения с поддержкой двух типов связей"""
    
    # Прямые связи для departments
    patient_department_status = models.ForeignKey(
        'departments.PatientDepartmentStatus',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='treatment_plans',
        verbose_name=_('Статус пациента в отделении')
    )
    
    # Прямая связь для encounters
    encounter = models.ForeignKey(
        'encounters.Encounter',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='treatment_plans',
        verbose_name=_('Случай обращения')
    )
    
    # GenericForeignKey для обратной совместимости
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey('content_type', 'object_id')
    
    # Общие поля
    name = models.CharField(_("Название плана"), max_length=200)
    description = models.TextField(_("Описание"), blank=True)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Создатель плана")
    )
    
    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(patient_department_status__isnull=False, encounter__isnull=True, content_type__isnull=True) |
                    models.Q(patient_department_status__isnull=True, encounter__isnull=False, content_type__isnull=True) |
                    models.Q(patient_department_status__isnull=True, encounter__isnull=True, content_type__isnull=False)
                ),
                name='single_owner_constraint_treatment'
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
        Получает или создает основной план лечения для указанного владельца
        
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
                defaults={'description': 'Основной план лечения'}
            )
        elif owner_type == 'encounter':
            from encounters.models import Encounter
            owner = Encounter.objects.get(pk=owner_id)
            plan, created = cls.objects.get_or_create(
                encounter=owner,
                name="Основной",
                defaults={'description': 'Основной план лечения'}
            )
        elif owner_type == 'generic' and owner_model:
            content_type = ContentType.objects.get_for_model(owner_model)
            owner = content_type.model_class().objects.get(pk=owner_id)
            plan, created = cls.objects.get_or_create(
                content_type=content_type,
                object_id=owner_id,
                name="Основной",
                defaults={'description': 'Основной план лечения'}
            )
        else:
            raise ValueError("Неверный тип владельца")
        
        return plan, created


from base.models import ArchivableModel
from base.services import ArchiveManager

class TreatmentPlan(ArchivableModel, BaseTreatmentPlan):
    """План лечения с поддержкой двух типов связей и архивирования"""
    
    class Meta:
        verbose_name = _("План лечения")
        verbose_name_plural = _("Планы лечения")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_department_status', 'created_at']),
            models.Index(fields=['encounter', 'created_at']),
            models.Index(fields=['content_type', 'object_id', 'created_at']),
        ]
    
    def __str__(self):
        owner_info = self.get_owner_display()
        return f"{self.name} ({owner_info})"
    
    def clean(self):
        """Проверка, что owner существует"""
        super().clean()
        if not self.patient_department_status and not self.encounter and not self.owner:
            raise ValidationError(_("Владелец плана лечения должен быть указан"))
    
    def get_owner_display(self):
        """Возвращает читаемое представление владельца"""
        return super().get_owner_display()
    
    def get_owner_model_name(self):
        """Возвращает имя модели владельца для использования в шаблонах"""
        return super().get_owner_model_name()
    
    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании TreatmentPlan"""
        # Архивируем связанные лекарства
        for medication in self.medications.all():
            if not medication.is_archived:
                if hasattr(medication, 'archive'):
                    medication.archive(user=user, reason=f"Архивирование связанного плана лечения: {reason}")
        
        # Архивируем связанные рекомендации
        for recommendation in self.recommendations.all():
            if not recommendation.is_archived:
                if hasattr(recommendation, 'archive'):
                    recommendation.archive(user=user, reason=f"Архивирование связанного плана лечения: {reason}")
        
        # Архивируем связанный статус в отделении
        if self.patient_department_status and not self.patient_department_status.is_archived:
            if hasattr(self.patient_department_status, 'archive'):
                self.patient_department_status.archive(user=user, reason=f"Архивирование связанного плана лечения: {reason}")
        
        # Архивируем связанный случай обращения
        if self.encounter and not self.encounter.is_archived:
            if hasattr(self.encounter, 'archive'):
                self.encounter.archive(user=user, reason=f"Архивирование связанного плана лечения: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении TreatmentPlan"""
        # Восстанавливаем связанные лекарства
        for medication in self.medications.all():
            if medication.is_archived:
                if hasattr(medication, 'restore'):
                    medication.restore(user=user)
        
        # Восстанавливаем связанные рекомендации
        for recommendation in self.recommendations.all():
            if recommendation.is_archived:
                if hasattr(recommendation, 'restore'):
                    recommendation.restore(user=user)
        
        # Восстанавливаем связанный статус в отделении
        if self.patient_department_status and self.patient_department_status.is_archived:
            if hasattr(self.patient_department_status, 'restore'):
                self.patient_department_status.restore(user=user)
        
        # Восстанавливаем связанный случай обращения
        if self.encounter and self.encounter.is_archived:
            if hasattr(self.encounter, 'restore'):
                self.encounter.restore(user=user)


class TreatmentMedication(ArchivableModel):
    """
    Назначение лекарства в плане лечения с поддержкой архивирования
    """
    treatment_plan = models.ForeignKey(
        TreatmentPlan, 
        on_delete=models.CASCADE, 
        verbose_name=_('План лечения'),
        related_name='medications'
    )
    medication = models.ForeignKey(
        Medication, 
        on_delete=models.CASCADE, 
        verbose_name=_('Лекарство'),
        related_name='treatment_medications'
    )
    dosage = models.CharField(_('Доза'), max_length=100)
    frequency = models.CharField(_('Частота'), max_length=100)
    route = models.ForeignKey(
        'pharmacy.AdministrationMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Путь введения'),
        help_text=_('Выберите способ введения препарата')
    )
    duration = models.CharField(_('Длительность'), max_length=100, blank=True)
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
        related_name='cancelled_medications'
    )
    cancellation_reason = models.TextField(_('Причина отмены'), blank=True)
    
    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = _('Назначение лекарства')
        verbose_name_plural = _('Назначения лекарств')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.medication.name} - {self.dosage} {self.frequency}"
    
    def get_medication_name(self):
        """Получить название лекарства"""
        return self.medication.name
    
    def get_schedule_frequency_display(self):
        """
        Возвращает частоту приема в часах на основе расписания
        Формула: 24 / количество раз в день
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self)
            appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.pk
            ).order_by('-scheduled_date', 'scheduled_time')
            
            if appointments.exists():
                # Группируем по дате и считаем количество записей для каждой даты
                from django.db.models import Count
                daily_counts = appointments.values('scheduled_date').annotate(
                    count=Count('id')
                ).order_by('-scheduled_date')
                
                if daily_counts.exists():
                    # Находим режим (наиболее частое значение)
                    count_frequency = {}
                    for daily_count in daily_counts:
                        count = daily_count['count']
                        count_frequency[count] = count_frequency.get(count, 0) + 1
                    
                    # Берем значение с максимальной частотой
                    most_common_count = max(count_frequency.items(), key=lambda x: x[1])[0]
                    
                    if most_common_count > 0:
                        hours_interval = 24 // most_common_count
                        if hours_interval == 24:
                            return f"1 раз в день"
                        elif hours_interval == 12:
                            return f"2 раза в день"
                        elif hours_interval == 8:
                            return f"3 раза в день"
                        elif hours_interval == 6:
                            return f"4 раза в день"
                        else:
                            return f"каждые {hours_interval} часов"
            
            # Если расписание не найдено, возвращаем базовую частоту
            return self.frequency if self.frequency else "Не указана"
            
        except Exception:
            return self.frequency if self.frequency else "Не указана"
    
    def get_schedule_duration_display(self):
        """
        Возвращает длительность курса в днях на основе расписания
        Рассчитывается как количество уникальных дат в ScheduledAppointment
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self)
            appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.pk
            ).order_by('scheduled_date')
            
            if appointments.exists():
                # Получаем уникальные даты
                unique_dates = appointments.values_list('scheduled_date', flat=True).distinct()
                duration_days = len(unique_dates)
                
                if duration_days > 0:
                    return f"{duration_days} дней"
            
            # Если расписание не найдено, возвращаем статичное значение
            return self.duration if self.duration else "Не указана"
            
        except Exception:
            return self.duration if self.duration else "Не указана"
    
    def get_schedule_start_datetime(self):
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
        # Для лекарств пока нет системы подписей, поэтому всегда можно отменить
        return True, None
    
    def cancel(self, reason="", cancelled_by=None):
        """
        Отменяет назначение
        """
        from django.utils import timezone
        
        can_cancel, error_message = self.can_be_cancelled()
        if not can_cancel:
            raise ValidationError(error_message)
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason'])
        
        # Синхронизируем с clinical_scheduling
        self._sync_with_clinical_scheduling()
    
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


class TreatmentRecommendation(ArchivableModel):
    """
    Рекомендация в плане лечения с поддержкой архивирования
    """
    treatment_plan = models.ForeignKey(
        TreatmentPlan, 
        on_delete=models.CASCADE, 
        verbose_name=_('План лечения'),
        related_name='recommendations'
    )
    text = models.TextField(_('Текст рекомендации'))
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
        related_name='cancelled_recommendations'
    )
    cancellation_reason = models.TextField(_('Причина отмены'), blank=True)
    
    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    class Meta:
        verbose_name = _('Рекомендация')
        verbose_name_plural = _('Рекомендации')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Рекомендация: {self.text[:50]}..."
    
    def get_schedule_start_datetime(self):
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
        # Для рекомендаций пока нет системы подписей, поэтому всегда можно отменить
        return True, None
    
    def cancel(self, reason="", cancelled_by=None):
        """
        Отменяет назначение
        """
        from django.utils import timezone
        
        can_cancel, error_message = self.can_be_cancelled()
        if not can_cancel:
            raise ValidationError(error_message)
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason'])
        
        # Синхронизируем с clinical_scheduling
        self._sync_with_clinical_scheduling()
    
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