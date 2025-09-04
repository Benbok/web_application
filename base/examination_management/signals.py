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
    
    Когда статус ExaminationInstrumental изменяется, автоматически обновляются
    соответствующие ScheduledAppointment в clinical_scheduling
    """
    if created:
        # Новое исследование - ничего не синхронизируем
        return
    
    # Получаем ContentType для ExaminationInstrumental
    content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
    
    # Находим все запланированные события для этого исследования
    scheduled_appointments = ScheduledAppointment.objects.filter(
        content_type=content_type,
        object_id=instance.pk
    )
    
    if not scheduled_appointments.exists():
        return
    
    # Обновляем статус запланированных событий в зависимости от статуса исследования
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


# ============================================================================
# СИГНАЛЫ ДЛЯ ОЧИСТКИ ЗАПИСЕЙ В CLINICAL_SCHEDULING ПРИ ФИЗИЧЕСКОМ УДАЛЕНИИ
# ============================================================================

@receiver(post_delete, sender=ExaminationLabTest)
def cleanup_examination_lab_test_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении лабораторного исследования
    
    ВНИМАНИЕ: Физическое удаление исследований не рекомендуется в медицинской системе!
    Используйте мягкое удаление (отмену) вместо этого.
    """
    try:
        content_type = ContentType.objects.get_for_model(ExaminationLabTest)
        
        # Находим и удаляем все связанные запланированные события
        deleted_count = ScheduledAppointment.objects.filter(
            content_type=content_type,
            object_id=instance.pk
        ).delete()[0]
        
        if deleted_count > 0:
            print(f"Удалено {deleted_count} записей в clinical_scheduling для ExaminationLabTest {instance.pk}")
            
    except Exception as e:
        print(f"Ошибка при очистке записей clinical_scheduling для ExaminationLabTest {instance.pk}: {e}")


@receiver(post_delete, sender=ExaminationInstrumental)
def cleanup_examination_instrumental_appointments(sender, instance, **kwargs):
    """
    Очищает запланированные события при физическом удалении инструментального исследования
    
    ВНИМАНИЕ: Физическое удаление исследований не рекомендуется в медицинской системе!
    Используйте мягкое удаление (отмену) вместо этого.
    """
    try:
        content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
        
        # Находим и удаляем все связанные запланированные события
        deleted_count = ScheduledAppointment.objects.filter(
            content_type=content_type,
            object_id=instance.pk
        ).delete()[0]
        
        if deleted_count > 0:
            print(f"Удалено {deleted_count} записей в clinical_scheduling для ExaminationInstrumental {instance.pk}")
            
    except Exception as e:
        print(f"Ошибка при очистке записей clinical_scheduling для ExaminationInstrumental {instance.pk}: {e}")


# ============================================================================
# СИГНАЛЫ ДЛЯ СИНХРОНИЗАЦИИ ОТМЕНЫ С LAB_TESTS И INSTRUMENTAL_PROCEDURES
# ============================================================================

@receiver(post_save, sender=ExaminationLabTest)
def sync_lab_test_cancellation(sender, instance, created, **kwargs):
    """
    Синхронизирует отмену лабораторного исследования с lab_tests
    
    Когда ExaminationLabTest отменяется, автоматически отменяется
    соответствующий LabTestResult в lab_tests
    """
    if created:
        # Новое исследование - ничего не синхронизируем
        return
    
    if instance.status == 'cancelled':
        try:
            from lab_tests.models import LabTestResult
            
            # Находим соответствующий результат лабораторного исследования
            lab_test_result = LabTestResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.lab_test
            ).first()
            
            if lab_test_result and lab_test_result.status != 'cancelled':
                # Отменяем результат исследования
                lab_test_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {instance.cancellation_reason}",
                    cancelled_by=instance.cancelled_by
                )
                print(f"Отменен LabTestResult {lab_test_result.pk} для ExaminationLabTest {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при синхронизации отмены с lab_tests: {e}")


@receiver(post_save, sender=ExaminationInstrumental)
def sync_instrumental_cancellation(sender, instance, created, **kwargs):
    """
    Синхронизирует отмену инструментального исследования с instrumental_procedures
    
    Когда ExaminationInstrumental отменяется, автоматически отменяется
    соответствующий InstrumentalProcedureResult в instrumental_procedures
    """
    if created:
        # Новое исследование - ничего не синхронизируем
        return
    
    if instance.status == 'cancelled':
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            
            # Находим соответствующий результат инструментального исследования
            instrumental_result = InstrumentalProcedureResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.instrumental_procedure
            ).first()
            
            if instrumental_result and instrumental_result.status != 'cancelled':
                # Отменяем результат исследования
                instrumental_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {instance.cancellation_reason}",
                    cancelled_by=instance.cancelled_by
                )
                print(f"Отменен InstrumentalProcedureResult {instrumental_result.pk} для ExaminationInstrumental {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при синхронизации отмены с instrumental_procedures: {e}")


# ============================================================================
# СУЩЕСТВУЮЩИЕ СИГНАЛЫ ДЛЯ СИНХРОНИЗАЦИИ ЗАВЕРШЕНИЯ
# ============================================================================

@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def sync_instrumental_result_completion(sender, instance, created, **kwargs):
    """
    Синхронизирует статус выполнения инструментального исследования
    когда данные результата заполнены
    """
    try:
        # Обновляем статус только при изменении, а не при создании
        if not created and instance.examination_instrumental:
            # Используем прямую связь с ExaminationInstrumental
            examination = instance.examination_instrumental
            
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
        if not created and instance.examination_lab_test:
            # Используем прямую связь с ExaminationLabTest
            examination = instance.examination_lab_test
            
            if instance.is_completed:
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


# ============================================================================
# СИГНАЛЫ ДЛЯ СОЗДАНИЯ РЕЗУЛЬТАТОВ ПРИ СОЗДАНИИ НАЗНАЧЕНИЙ
# ============================================================================

@receiver(post_save, sender=ExaminationLabTest)
def create_lab_test_result(sender, instance, created, **kwargs):
    """
    Создает запись результата лабораторного исследования при создании назначения
    """
    if created:
        try:
            from lab_tests.models import LabTestResult
            
            # Проверяем, есть ли уже результат для этого конкретного назначения
            existing_result = LabTestResult.objects.filter(
                examination_lab_test=instance
            ).first()
            
            if not existing_result:
                # Получаем пользователя из владельца плана
                owner = instance.examination_plan.get_owner()
                author = None
                
                if owner:
                    if hasattr(owner, 'doctor'):
                        # Для Encounter используем поле doctor
                        author = owner.doctor
                    elif hasattr(owner, 'accepted_by'):
                        # Для PatientDepartmentStatus используем поле accepted_by
                        author = owner.accepted_by
                    elif hasattr(owner, 'get_user'):
                        # Fallback для других типов владельцев
                        author = owner.get_user()
                
                # Создаем новый результат
                LabTestResult.objects.create(
                    patient=instance.examination_plan.get_patient(),
                    examination_plan=instance.examination_plan,
                    procedure_definition=instance.lab_test,
                    examination_lab_test=instance,  # Связываем с конкретным назначением
                    author=author
                )
                print(f"Создан LabTestResult для ExaminationLabTest {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при создании LabTestResult: {e}")


@receiver(post_save, sender=ExaminationInstrumental)
def create_instrumental_procedure_result(sender, instance, created, **kwargs):
    """
    Создает запись результата инструментального исследования при создании назначения
    """
    if created:
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            
            # Проверяем, есть ли уже результат для этого конкретного назначения
            existing_result = InstrumentalProcedureResult.objects.filter(
                examination_instrumental=instance
            ).first()
            
            if not existing_result:
                # Получаем пользователя из владельца плана
                owner = instance.examination_plan.get_owner()
                author = None
                
                if owner:
                    if hasattr(owner, 'doctor'):
                        # Для Encounter используем поле doctor
                        author = owner.doctor
                    elif hasattr(owner, 'accepted_by'):
                        # Для PatientDepartmentStatus используем поле accepted_by
                        author = owner.accepted_by
                    elif hasattr(owner, 'get_user'):
                        # Fallback для других типов владельцев
                        author = owner.get_user()
                
                # Создаем новый результат
                InstrumentalProcedureResult.objects.create(
                    patient=instance.examination_plan.get_patient(),
                    examination_plan=instance.examination_plan,
                    procedure_definition=instance.instrumental_procedure,
                    examination_instrumental=instance,  # Связываем с конкретным назначением
                    author=author
                )
                print(f"Создан InstrumentalProcedureResult для ExaminationInstrumental {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при создании InstrumentalProcedureResult: {e}") 