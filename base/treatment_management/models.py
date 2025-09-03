from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from pharmacy.models import Medication


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


from .mixins import SoftDeleteMixin
from base.models import ArchivableModel
from base.services import ArchiveManager

class TreatmentPlan(ArchivableModel, BaseTreatmentPlan, SoftDeleteMixin):
    """План лечения с поддержкой двух типов связей и мягкого удаления"""
    
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


class TreatmentMedication(ArchivableModel, SoftDeleteMixin):
    """
    Лекарство в плане лечения с поддержкой мягкого удаления
    """
    
    treatment_plan = models.ForeignKey(
        TreatmentPlan, 
        on_delete=models.CASCADE, 
        related_name='medications',
        verbose_name=_("План лечения")
    )
    
    # Препарат из справочника или собственный
    medication = models.ForeignKey(
        Medication, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Препарат из справочника")
    )
    custom_medication = models.CharField(
        _("Собственный препарат"), 
        max_length=200, 
        blank=True,
        help_text=_("Введите название препарата, если его нет в справочнике")
    )
    
    # Параметры назначения
    dosage = models.CharField(_("Дозировка"), max_length=100)
    frequency = models.CharField(_("Частота приема"), max_length=100)
    route = models.ForeignKey(
        'pharmacy.AdministrationMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Способ введения"),
        help_text=_("Выберите способ введения препарата")
    )
    duration = models.CharField(_("Длительность"), max_length=100, blank=True)
    instructions = models.TextField(_("Особые указания"), blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)
    
    class Meta:
        verbose_name = _("Лекарство в плане лечения")
        verbose_name_plural = _("Лекарства в планах лечения")
        ordering = ['-created_at']
    
    def __str__(self):
        medication_name = self.get_medication_name()
        return f"{medication_name} - {self.dosage} {self.frequency}"
    
    def clean(self):
        """Проверка, что указан либо препарат из справочника, либо собственный"""
        if not self.medication and not self.custom_medication:
            raise ValidationError(
                _("Необходимо указать либо препарат из справочника, либо собственный препарат")
            )
        if self.medication and self.custom_medication:
            raise ValidationError(
                _("Нельзя указывать одновременно препарат из справочника и собственный препарат")
            )
    
    def get_medication_name(self):
        """Возвращает название препарата"""
        if self.medication:
            return self.medication.name
        return self.custom_medication
    
    def get_route_display_name(self):
        """Возвращает читаемое название способа введения"""
        if self.route:
            return self.route.name
        return _("Не указан")
    
    def get_external_info_url(self):
        """Возвращает ссылку на внешнюю информацию о препарате"""
        if self.medication and self.medication.external_info_url:
            return self.medication.external_info_url
        return None
    
    def get_medication_form(self):
        """Возвращает лекарственную форму препарата"""
        if self.medication and hasattr(self.medication, 'medication_form'):
            return self.medication.medication_form
        return None
    
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
                ).order_by('scheduled_date')
                
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
    
    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании TreatmentMedication"""
        # Архивируем связанный план лечения
        if self.treatment_plan and not self.treatment_plan.is_archived:
            if hasattr(self.treatment_plan, 'archive'):
                self.treatment_plan.archive(user=user, reason=f"Архивирование связанного лекарства: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении TreatmentMedication"""
        # Восстанавливаем связанный план лечения
        if self.treatment_plan and self.treatment_plan.is_archived:
            if hasattr(self.treatment_plan, 'restore'):
                self.treatment_plan.restore(user=user)


class TreatmentRecommendation(ArchivableModel, SoftDeleteMixin):
    """
    Рекомендации в плане лечения с поддержкой мягкого удаления
    """
    treatment_plan = models.ForeignKey(
        TreatmentPlan, 
        on_delete=models.CASCADE, 
        related_name='recommendations',
        verbose_name=_("План лечения")
    )
    
    text = models.TextField(_("Текст рекомендации"), help_text=_("Введите рекомендацию"))
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)
    
    class Meta:
        verbose_name = _("Рекомендация в плане лечения")
        verbose_name_plural = _("Рекомендации в планах лечения")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.text[:50]}..." if len(self.text) > 50 else self.text
    
    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании TreatmentRecommendation"""
        # Архивируем связанный план лечения
        if self.treatment_plan and not self.treatment_plan.is_archived:
            if hasattr(self.treatment_plan, 'archive'):
                self.treatment_plan.archive(user=user, reason=f"Архивирование связанной рекомендации: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении TreatmentRecommendation"""
        # Восстанавливаем связанный план лечения
        if self.treatment_plan and self.treatment_plan.is_archived:
            if hasattr(self.treatment_plan, 'restore'):
                self.treatment_plan.restore(user=user)
    
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