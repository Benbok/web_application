from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import InstrumentalProcedureResult
from clinical_scheduling.models import ScheduledAppointment


@receiver(post_save, sender=InstrumentalProcedureResult)
def sync_instrumental_procedure_result_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус результата инструментального исследования с запланированными событиями
    
    Когда создается результат исследования, соответствующие запланированные события
    помечаются как завершенные
    """
    if not created:
        # Обновление результата - ничего не синхронизируем
        return
    
    # Получаем ContentType для InstrumentalProcedureResult
    content_type = ContentType.objects.get_for_model(InstrumentalProcedureResult)
    
    # Находим все запланированные события для этого результата
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    # Помечаем все связанные события как завершенные
    for appointment in scheduled_appointments:
        if appointment.execution_status == 'scheduled':
            appointment.execution_status = 'completed'
            appointment.executed_at = timezone.now()
            appointment.save(update_fields=['execution_status', 'executed_at'])


@receiver(post_delete, sender=InstrumentalProcedureResult)
def cleanup_instrumental_procedure_result_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении результата
    
    ВНИМАНИЕ: Физическое удаление результатов не рекомендуется в медицинской системе!
    """
    content_type = ContentType.objects.get_for_model(InstrumentalProcedureResult)
    
    # Находим и удаляем все связанные запланированные события
    ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    ).delete() 