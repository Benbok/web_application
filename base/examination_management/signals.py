from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import ExaminationLabTest, ExaminationInstrumental
from clinical_scheduling.models import ScheduledAppointment
from .services import ExaminationIntegrationService


@receiver(post_save, sender=ExaminationLabTest)
def sync_examination_lab_test_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус лабораторного исследования с запланированными событиями
    
    Когда статус ExaminationLabTest изменяется, автоматически обновляются
    соответствующие ScheduledAppointment в clinical_scheduling
    """
    if created:
        # Новое исследование - ничего не синхронизируем
        return
    
    # Получаем ContentType для ExaminationLabTest
    content_type = ContentType.objects.get_for_model(ExaminationLabTest)
    
    # Находим все запланированные события для этого исследования
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    # Обновляем статус запланированных событий в зависимости от статуса исследования
    # Используем status из ArchivableModel
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


@receiver(post_save, sender=ExaminationInstrumental)
def sync_examination_instrumental_status(sender, instance, created, **kwargs):
    """
    Синхронизирует статус инструментального исследования с запланированными событиями
    
    Аналогично ExaminationLabTest, но для инструментальных исследований
    """
    if created:
        return
    
    content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
    
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    # Обновляем статус запланированных событий в зависимости от статуса исследования
    # Используем status из ArchivableModel
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


@receiver(post_delete, sender=ExaminationLabTest)
def cleanup_examination_lab_test_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении исследования
    
    ВНИМАНИЕ: Физическое удаление исследований не рекомендуется в медицинской системе!
    Используйте мягкое удаление (отмену) вместо этого.
    """
    content_type = ContentType.objects.get_for_model(ExaminationLabTest)
    
    # Находим и удаляем все связанные запланированные события
    ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    ).delete()


@receiver(post_delete, sender=ExaminationInstrumental)
def cleanup_examination_instrumental_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении инструментального исследования
    """
    content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
    
    ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    ).delete()


@receiver(post_save, sender=ExaminationLabTest)
def create_lab_test_result_on_save(sender, instance, created, **kwargs):
    """
    Автоматически создает запись результата в lab_tests при создании ExaminationLabTest
    """
    if created:
        try:
            # Получаем пользователя из examination_plan.created_by или используем системного пользователя
            user = instance.examination_plan.created_by
            if not user:
                # Если нет пользователя, создаем системного
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user, _ = User.objects.get_or_create(
                    username='system_integration',
                    defaults={'is_active': False}
                )
            
            # Создаем результат через сервис интеграции
            ExaminationIntegrationService.create_lab_test_result(instance, user)
            
        except Exception as e:
            print(f"Ошибка при автоматическом создании результата лабораторного исследования: {e}")


@receiver(post_save, sender=ExaminationInstrumental)
def create_instrumental_procedure_result_on_save(sender, instance, created, **kwargs):
    """
    Автоматически создает запись результата в instrumental_procedures при создании ExaminationInstrumental
    """
    if created:
        try:
            # Получаем пользователя из examination_plan.created_by или используем системного пользователя
            user = instance.examination_plan.created_by
            if not user:
                # Если нет пользователя, создаем системного
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user, _ = User.objects.get_or_create(
                    username='system_integration',
                    defaults={'is_active': False}
                )
            
            # Создаем результат через сервис интеграции
            ExaminationIntegrationService.create_instrumental_procedure_result(instance, user)
            
        except Exception as e:
            print(f"Ошибка при автоматическом создании результата инструментального исследования: {e}")


# Сигналы для синхронизации статусов при заполнении данных
@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def sync_instrumental_result_completion(sender, instance, created, **kwargs):
    """
    Синхронизирует статус выполнения инструментального исследования
    когда данные результата заполнены
    """
    try:
        # Обновляем статус только при изменении, а не при создании
        if not created and instance.examination_plan:
            # Ищем ExaminationInstrumental для этого плана и типа процедуры
            from .models import ExaminationInstrumental
            examination = ExaminationInstrumental.objects.filter(
                examination_plan=instance.examination_plan,
                instrumental_procedure=instance.procedure_definition
            ).first()
            
            if examination and instance.is_completed:
                # Если данные заполнены, обновляем статус в examination_management
                examination.status = 'completed'
                examination.completed_at = timezone.now()
                examination.completed_by = instance.author
                examination.save()
                
                # Обновляем статус в clinical_scheduling
                from .services import ExaminationStatusService
                ExaminationStatusService.update_assignment_status(
                    examination, 'completed', instance.author, 'Данные результата заполнены'
                )
                
    except Exception as e:
        print(f"Ошибка при синхронизации статуса инструментального исследования: {e}")


@receiver(post_save, sender='lab_tests.LabTestResult')
def sync_lab_test_result_completion(sender, instance, created, **kwargs):
    """
    Синхронизирует статус выполнения лабораторного исследования
    когда данные результата заполнены
    """
    try:
        # Обновляем статус только при изменении, а не при создании
        if not created and instance.examination_plan:
            # Ищем ExaminationLabTest для этого плана и типа исследования
            from .models import ExaminationLabTest
            examination = ExaminationLabTest.objects.filter(
                examination_plan=instance.examination_plan,
                lab_test=instance.procedure_definition
            ).first()
            
            if examination and instance.is_completed:
                # Если данные заполнены, обновляем статус в examination_management
                examination.status = 'completed'
                examination.completed_at = timezone.now()
                examination.completed_by = instance.author
                examination.save()
                
                # Обновляем статус в clinical_scheduling
                from .services import ExaminationStatusService
                ExaminationStatusService.update_assignment_status(
                    examination, 'completed', instance.author, 'Данные результата заполнены'
                )
                
    except Exception as e:
        print(f"Ошибка при синхронизации статуса лабораторного исследования: {e}") 