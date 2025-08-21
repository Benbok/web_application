from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import LabTestResult
from clinical_scheduling.models import ScheduledAppointment


@receiver(post_save, sender=LabTestResult)
def sync_lab_test_result_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус результата лабораторного исследования с запланированными событиями
    
    Когда создается результат исследования, соответствующие запланированные события
    помечаются как завершенные
    """
    if not created:
        # Обновление результата - ничего не синхронизируем
        return
    
    # Получаем ContentType для LabTestResult
    content_type = ContentType.objects.get_for_model(LabTestResult)
    
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


@receiver(post_delete, sender=LabTestResult)
def cleanup_lab_test_result_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении результата
    
    ВНИМАНИЕ: Физическое удаление результатов не рекомендуется в медицинской системе!
    """
    content_type = ContentType.objects.get_for_model(LabTestResult)
    
    # Находим и удаляем все связанные запланированные события
    ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    ).delete() 