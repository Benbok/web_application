from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation
from clinical_scheduling.models import ScheduledAppointment


@receiver(post_save, sender=TreatmentPlan)
def sync_treatment_plan_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус плана лечения с запланированными событиями
    
    Когда статус TreatmentPlan изменяется, автоматически обновляются
    соответствующие ScheduledAppointment в clinical_scheduling
    """
    if created:
        # Новый план - ничего не синхронизируем
        return
    
    # Получаем ContentType для TreatmentPlan
    content_type = ContentType.objects.get_for_model(TreatmentPlan)
    
    # Находим все запланированные события для этого плана
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    # Обновляем статус запланированных событий в зависимости от статуса плана
    if instance.status == 'cancelled':
        # Отменяем все будущие запланированные события
        future_appointments = scheduled_appointments.filter(
            scheduled_date__gte=timezone.now().date()
        )
        
        for appointment in future_appointments:
            appointment.execution_status = 'canceled'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'paused':
        # Приостанавливаем все будущие запланированные события
        future_appointments = scheduled_appointments.filter(
            scheduled_date__gte=timezone.now().date()
        )
        
        for appointment in future_appointments:
            appointment.execution_status = 'skipped'  # Пропускаем на время приостановки
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'active':
        # Возобновляем приостановленные события
        paused_appointments = scheduled_appointments.filter(
            execution_status='skipped'
        )
        
        for appointment in paused_appointments:
            appointment.execution_status = 'scheduled'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'completed':
        # Помечаем все события как завершенные
        for appointment in scheduled_appointments:
            if appointment.execution_status == 'scheduled':
                appointment.execution_status = 'completed'
                appointment.executed_at = timezone.now()
                appointment.save(update_fields=['execution_status', 'executed_at'])


@receiver(post_save, sender=TreatmentMedication)
def sync_treatment_medication_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус назначения лекарства с запланированными событиями
    
    Когда статус TreatmentMedication изменяется, автоматически обновляются
    соответствующие ScheduledAppointment в clinical_scheduling
    """
    if created:
        # Новое назначение - ничего не синхронизируем
        return
    
    # Получаем ContentType для TreatmentMedication
    content_type = ContentType.objects.get_for_model(TreatmentMedication)
    
    # Находим все запланированные события для этого назначения
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    # Обновляем статус запланированных событий в зависимости от статуса назначения
    if instance.status == 'cancelled':
        # Отменяем все будущие запланированные события
        future_appointments = scheduled_appointments.filter(
            scheduled_date__gte=timezone.now().date()
        )
        
        for appointment in future_appointments:
            appointment.execution_status = 'canceled'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'paused':
        # Приостанавливаем все будущие запланированные события
        future_appointments = scheduled_appointments.filter(
            scheduled_date__gte=timezone.now().date()
        )
        
        for appointment in future_appointments:
            appointment.execution_status = 'skipped'  # Пропускаем на время приостановки
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'active':
        # Возобновляем приостановленные события
        paused_appointments = scheduled_appointments.filter(
            execution_status='skipped'
        )
        
        for appointment in paused_appointments:
            appointment.execution_status = 'scheduled'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'completed':
        # Помечаем все события как завершенные
        for appointment in scheduled_appointments:
            if appointment.execution_status == 'scheduled':
                appointment.execution_status = 'completed'
                appointment.executed_at = timezone.now()
                appointment.save(update_fields=['execution_status', 'executed_at'])


@receiver(post_save, sender=TreatmentRecommendation)
def sync_treatment_recommendation_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус рекомендации с запланированными событиями
    
    Аналогично TreatmentMedication, но для рекомендаций
    """
    if created:
        return
    
    content_type = ContentType.objects.get_for_model(TreatmentRecommendation)
    
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    if instance.status == 'cancelled':
        future_appointments = scheduled_appointments.filter(
            scheduled_date__gte=timezone.now().date()
        )
        
        for appointment in future_appointments:
            appointment.execution_status = 'canceled'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'paused':
        future_appointments = scheduled_appointments.filter(
            scheduled_date__gte=timezone.now().date()
        )
        
        for appointment in future_appointments:
            appointment.execution_status = 'skipped'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'active':
        paused_appointments = scheduled_appointments.filter(
            execution_status='skipped'
        )
        
        for appointment in paused_appointments:
            appointment.execution_status = 'scheduled'
            appointment.save(update_fields=['execution_status'])
            
    elif instance.status == 'completed':
        for appointment in scheduled_appointments:
            if appointment.execution_status == 'scheduled':
                appointment.execution_status = 'completed'
                appointment.executed_at = timezone.now()
                appointment.save(update_fields=['execution_status', 'executed_at'])


@receiver(post_delete, sender=TreatmentMedication)
def cleanup_treatment_medication_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении назначения
    
    ВНИМАНИЕ: Физическое удаление назначений не рекомендуется в медицинской системе!
    Используйте мягкое удаление (отмену) вместо этого.
    """
    content_type = ContentType.objects.get_for_model(TreatmentMedication)
    
    # Находим и удаляем все связанные запланированные события
    ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    ).delete()


@receiver(post_delete, sender=TreatmentRecommendation)
def cleanup_treatment_recommendation_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении рекомендации
    """
    content_type = ContentType.objects.get_for_model(TreatmentRecommendation)
    
    ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    ).delete() 