from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import ExaminationPlan
from django.utils import timezone


class ExaminationPlanService:
    """
    Сервис для управления планами обследования
    """
    
    @staticmethod
    def create_examination_plan(owner, name, description='', priority='normal', created_by=None):
        """
        Создает новый план обследования для указанного владельца
        
        Args:
            owner: Объект-владелец (encounter, department_stay, etc.)
            name: Название плана
            description: Описание плана
            priority: Приоритет плана
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
                created_by=created_by
            )
        elif owner_model_name == 'encounter':
            examination_plan = ExaminationPlan.objects.create(
                encounter=owner,
                name=name,
                description=description,
                priority=priority,
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
    Сервис для управления статусами назначений
    """
    
    @staticmethod
    def get_assignment_status(assignment):
        """
        Получает корректный статус назначения на основе всех условий
        
        Args:
            assignment: ExaminationLabTest или ExaminationInstrumental
            
        Returns:
            dict: Информация о статусе
        """
        try:
            # 0. Проверяем статус отмены в самом назначении
            if hasattr(assignment, 'status') and assignment.status == 'cancelled':
                return {
                    'status': 'cancelled',
                    'status_display': 'Отменено',
                    'completed_by': assignment.cancelled_by,
                    'end_date': assignment.cancelled_at,
                    'rejection_reason': assignment.cancellation_reason,
                    'assignment_id': None,
                    'has_results': False,
                    'reason': 'Назначение отменено'
                }
            
            # 1. Проверяем, есть ли результат
            result = ExaminationStatusService._get_result(assignment)
            
            if result:
                # 2. Если результат есть, проверяем его заполненность
                if result.is_completed:
                    # 3. Проверяем подписи (если приложение установлено)
                    if ExaminationStatusService._is_document_signed(result):
                        return {
                            'status': 'completed',
                            'status_display': 'Выполнено',
                            'completed_by': result.author,
                            'end_date': result.updated_at,
                            'rejection_reason': None,
                            'assignment_id': None,
                            'has_results': True,
                            'reason': 'Результат заполнен и подписан'
                        }
                    else:
                        return {
                            'status': 'active',
                            'status_display': 'Ожидает подписи',
                            'completed_by': None,
                            'end_date': None,
                            'rejection_reason': None,
                            'assignment_id': None,
                            'has_results': True,
                            'reason': 'Результат заполнен, ожидает подписи'
                        }
                else:
                    return {
                        'status': 'active',
                        'status_display': 'Ожидает заполнения',
                        'completed_by': None,
                        'end_date': None,
                        'rejection_reason': None,
                        'assignment_id': None,
                        'has_results': True,
                        'reason': 'Результат создан, но не заполнен'
                    }
            
            # 4. Если результата нет, проверяем clinical_scheduling
            scheduled_appointment = ExaminationStatusService._get_scheduled_appointment(assignment)
            
            if scheduled_appointment:
                return {
                    'status': scheduled_appointment.execution_status,
                    'status_display': scheduled_appointment.get_execution_status_display(),
                    'completed_by': scheduled_appointment.executed_by,
                    'end_date': scheduled_appointment.executed_at,
                    'rejection_reason': scheduled_appointment.rejection_reason,
                    'assignment_id': scheduled_appointment.pk,
                    'has_results': False,
                    'reason': 'Статус из clinical_scheduling'
                }
            
            # 5. По умолчанию - запланировано
            return {
                'status': 'scheduled',
                'status_display': 'Запланировано',
                'completed_by': None,
                'end_date': None,
                'rejection_reason': None,
                'assignment_id': None,
                'has_results': False,
                'reason': 'Назначение создано, ожидает планирования'
            }
            
        except Exception as e:
            print(f"Ошибка при получении статуса назначения: {e}")
            return {
                'status': 'unknown',
                'status_display': 'Неизвестно',
                'completed_by': None,
                'end_date': None,
                'rejection_reason': None,
                'assignment_id': None,
                'has_results': False,
                'reason': f'Ошибка: {str(e)}'
            }
    
    @staticmethod
    def _get_result(assignment):
        """Получает результат назначения"""
        try:
            if hasattr(assignment, 'lab_test'):
                # Это ExaminationLabTest
                from lab_tests.models import LabTestResult
                return LabTestResult.objects.filter(
                    examination_plan=assignment.examination_plan,
                    procedure_definition=assignment.lab_test
                ).first()
            elif hasattr(assignment, 'instrumental_procedure'):
                # Это ExaminationInstrumental
                from instrumental_procedures.models import InstrumentalProcedureResult
                return InstrumentalProcedureResult.objects.filter(
                    examination_plan=assignment.examination_plan,
                    procedure_definition=assignment.instrumental_procedure
                ).first()
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_scheduled_appointment(assignment):
        """Получает запланированное событие из clinical_scheduling"""
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(assignment.__class__)
            return ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=assignment.pk
            ).first()
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_schedule_data(assignment):
        """
        Получает данные расписания для назначения
        
        Args:
            assignment: ExaminationLabTest или ExaminationInstrumental
            
        Returns:
            dict: Данные расписания или None
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(assignment.__class__)
            appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=assignment.pk
            ).order_by('scheduled_date', 'scheduled_time')
            
            if appointments.exists():
                # Берем первое назначение для получения базовых данных
                first_appointment = appointments.first()
                
                # Подсчитываем общее количество назначений
                total_appointments = appointments.count()
                
                # Вычисляем частоту (24 / количество раз в день)
                times_per_day = 1  # По умолчанию
                if total_appointments > 0:
                    # Пытаемся вычислить количество раз в день
                    # Для этого смотрим на интервал между первым и вторым назначением
                    if appointments.count() > 1:
                        second_appointment = appointments[1]
                        time_diff = second_appointment.scheduled_time.hour - first_appointment.scheduled_time.hour
                        if time_diff > 0:
                            times_per_day = 24 // time_diff
                        else:
                            times_per_day = 1
                
                frequency_hours = 24 // times_per_day if times_per_day > 0 else 24
                
                return {
                    'assigned_at': first_appointment.scheduled_date,
                    'first_time': first_appointment.scheduled_time,
                    'frequency': f'каждые {frequency_hours} часов',
                    'duration_days': total_appointments,
                    'times_per_day': times_per_day,
                    'total_appointments': total_appointments
                }
            
            return None
            
        except Exception as e:
            print(f"Ошибка при получении данных расписания: {e}")
            return None
    
    @staticmethod
    def _is_document_signed(result):
        """Проверяет, подписан ли документ"""
        try:
            from document_signatures.models import DocumentSignature
            signatures = DocumentSignature.objects.filter(
                content_type__model=result._meta.model_name.lower(),
                object_id=result.pk
            )
            return signatures.exists() and signatures.filter(status='signed').exists()
        except Exception:
            return False
    
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
            
            # Проверяем, не существует ли уже результат для этого конкретного назначения
            existing_result = LabTestResult.objects.filter(
                examination_lab_test=examination_lab_test
            ).first()
            
            if existing_result:
                return existing_result
            
            # Создаем новый результат
            result = LabTestResult.objects.create(
                patient=examination_lab_test.examination_plan.get_patient(),
                procedure_definition=examination_lab_test.lab_test,
                examination_plan=examination_lab_test.examination_plan,
                examination_lab_test=examination_lab_test,  # Связываем с конкретным назначением
                author=user,
                datetime_result=timezone.now(),
                data={},  # Пустые данные, которые заполнит врач/лаборант
                is_completed=False  # Данные еще не заполнены
            )
            
            return result
            
        except Exception as e:
            print(f"Ошибка при создании результата лабораторного исследования: {e}")
            return None 