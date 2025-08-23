from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import ExaminationPlan
from django.utils import timezone


class ExaminationPlanService:
    """
    Сервис для управления планами обследования
    """
    
    @staticmethod
    def create_examination_plan(owner, name, description='', priority='normal', is_active=True, created_by=None):
        """
        Создает новый план обследования для указанного владельца
        
        Args:
            owner: Объект-владелец (encounter, department_stay, etc.)
            name: Название плана
            description: Описание плана
            priority: Приоритет плана
            is_active: Активен ли план
            created_by: Создатель плана
        
        Returns:
            ExaminationPlan: Созданный план обследования
        """
        # Определяем тип владельца по имени модели и устанавливаем соответствующее поле
        owner_model_name = owner._meta.model_name if hasattr(owner, '_meta') else None
        if owner_model_name == 'patientdepartmentstatus':
            examination_plan = ExaminationPlan.objects.create(
                patient_department_status=owner,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        elif owner_model_name == 'encounter':
            examination_plan = ExaminationPlan.objects.create(
                encounter=owner,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        else:
            # Для обратной совместимости используем GenericForeignKey
            content_type = ContentType.objects.get_for_model(owner)
            examination_plan = ExaminationPlan.objects.create(
                content_type=content_type,
                object_id=owner.id,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        
        return examination_plan
    
    @staticmethod
    def get_examination_plans(owner):
        """
        Получает все планы обследования для указанного владельца
        
        Args:
            owner: Объект-владелец
        
        Returns:
            QuerySet: Планы обследования
        """
        # Определяем тип владельца по имени модели и используем соответствующее поле
        owner_model_name = owner._meta.model_name if hasattr(owner, '_meta') else None
        if owner_model_name == 'patientdepartmentstatus':
            return ExaminationPlan.objects.filter(patient_department_status=owner)
        elif owner_model_name == 'encounter':
            return ExaminationPlan.objects.filter(encounter=owner)
        else:
            # Для обратной совместимости используем GenericForeignKey
            content_type = ContentType.objects.get_for_model(owner)
            return ExaminationPlan.objects.filter(
                content_type=content_type,
                object_id=owner.id
            )
    
    @staticmethod
    def delete_examination_plan(examination_plan):
        """
        Удаляет план обследования и все связанные исследования
        
        Args:
            examination_plan: План обследования для удаления
        """
        with transaction.atomic():
            examination_plan.delete() 


class ExaminationStatusService:
    """
    Сервис для управления статусами назначений через clinical_scheduling
    """
    
    @staticmethod
    def get_assignment_status(examination_item):
        """
        Получает статус назначения из clinical_scheduling
        
        Args:
            examination_item: ExaminationLabTest или ExaminationInstrumental
            
        Returns:
            dict: Информация о статусе назначения
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(examination_item.__class__)
            scheduled_appointment = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=examination_item.pk
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
            
            return None
            
        except Exception as e:
            print(f"Ошибка при получении статуса назначения: {e}")
            return None
    
    @staticmethod
    def update_assignment_status(examination_item, new_status, user=None, notes=''):
        """
        Обновляет статус назначения в clinical_scheduling
        
        Args:
            examination_item: ExaminationLabTest или ExaminationInstrumental
            new_status: Новый статус ('completed', 'rejected', 'skipped', etc.)
            user: Пользователь, выполняющий действие
            notes: Примечания к изменению статуса
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(examination_item.__class__)
            scheduled_appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=examination_item.pk
            )
            
            if scheduled_appointments.exists():
                for appointment in scheduled_appointments:
                    if new_status == 'completed':
                        appointment.mark_as_completed(user, notes)
                    elif new_status == 'rejected':
                        appointment.mark_as_rejected(user, notes)
                    elif new_status == 'skipped':
                        appointment.mark_as_skipped(user, notes)
                    elif new_status == 'partial':
                        appointment.mark_as_partial(user, notes, '')
                    else:
                        appointment.execution_status = new_status
                        appointment.save(update_fields=['execution_status'])
                        
        except Exception as e:
            print(f"Ошибка при обновлении статуса назначения: {e}")
    
    @staticmethod
    def create_schedule_for_assignment(examination_item, user, start_date=None, first_time=None, times_per_day=1, duration_days=1):
        """
        Создает расписание для назначения через clinical_scheduling
        
        Args:
            examination_item: ExaminationLabTest или ExaminationInstrumental
            user: Пользователь, создающий расписание
            start_date: Дата начала
            first_time: Время выполнения
            times_per_day: Количество раз в день
            duration_days: Длительность курса
            
        Returns:
            list: Список созданных запланированных событий
        """
        try:
            from clinical_scheduling.services import ClinicalSchedulingService
            
            return ClinicalSchedulingService.create_schedule_for_assignment(
                assignment=examination_item,
                user=user,
                start_date=start_date,
                first_time=first_time,
                times_per_day=times_per_day,
                duration_days=duration_days
            )
            
        except Exception as e:
            print(f"Ошибка при создании расписания: {e}")
            return [] 


class ExaminationIntegrationService:
    """
    Сервис для интеграции examination_management с другими приложениями
    """
    
    @staticmethod
    def create_instrumental_procedure_result(examination_instrumental, user):
        """
        Создает запись результата инструментального исследования в instrumental_procedures
        при создании ExaminationInstrumental
        """
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            
            # Проверяем, не существует ли уже результат для этого назначения
            existing_result = InstrumentalProcedureResult.objects.filter(
                patient=examination_instrumental.examination_plan.get_patient(),
                procedure_definition=examination_instrumental.instrumental_procedure,
                examination_plan=examination_instrumental.examination_plan
            ).first()
            
            if existing_result:
                return existing_result
            
            # Создаем новый результат
            result = InstrumentalProcedureResult.objects.create(
                patient=examination_instrumental.examination_plan.get_patient(),
                procedure_definition=examination_instrumental.instrumental_procedure,
                examination_plan=examination_instrumental.examination_plan,
                author=user,
                datetime_result=timezone.now(),
                data={},  # Пустые данные, которые заполнит врач/лаборант
                is_completed=False  # Данные еще не заполнены
            )
            
            return result
            
        except Exception as e:
            print(f"Ошибка при создании результата инструментального исследования: {e}")
            return None
    
    @staticmethod
    def create_lab_test_result(examination_lab_test, user):
        """
        Создает запись результата лабораторного исследования в lab_tests
        при создании ExaminationLabTest
        """
        try:
            from lab_tests.models import LabTestResult
            
            # Проверяем, не существует ли уже результат для этого назначения
            existing_result = LabTestResult.objects.filter(
                patient=examination_lab_test.examination_plan.get_patient(),
                procedure_definition=examination_lab_test.lab_test,
                examination_plan=examination_lab_test.examination_plan
            ).first()
            
            if existing_result:
                return existing_result
            
            # Создаем новый результат
            result = LabTestResult.objects.create(
                patient=examination_lab_test.examination_plan.get_patient(),
                procedure_definition=examination_lab_test.lab_test,
                examination_plan=examination_lab_test.examination_plan,
                author=user,
                datetime_result=timezone.now(),
                data={},  # Пустые данные, которые заполнит врач/лаборант
                is_completed=False  # Данные еще не заполнены
            )
            
            return result
            
        except Exception as e:
            print(f"Ошибка при создании результата лабораторного исследования: {e}")
            return None 