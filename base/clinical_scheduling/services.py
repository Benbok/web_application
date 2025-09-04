from django.utils import timezone
from datetime import timedelta, time
from django.contrib.contenttypes.models import ContentType
from .models import ScheduledAppointment
from departments.models import PatientDepartmentStatus, Department

class ClinicalSchedulingService:
    @staticmethod
    def create_schedule_for_assignment(assignment, user, start_date=None, first_time=None, times_per_day=None, duration_days=None):
        """
        Создает расписание для назначения
        
        Args:
            assignment: Назначение (TreatmentMedication, ExaminationLabTest, etc.)
            user: Пользователь, создающий расписание
            start_date: Дата начала (по умолчанию - сегодня)
            first_time: Время первого приема (по умолчанию - 09:00)
            times_per_day: Количество приемов в день (по умолчанию - 1)
            duration_days: Длительность курса в днях (по умолчанию - 7)
        """

        
        if not start_date:
            start_date = timezone.now().date()
        if not first_time:
            first_time = time(9, 0)
        if not times_per_day:
            times_per_day = 1
        if not duration_days:
            duration_days = 7

        
        # Получаем информацию о пациенте, отделении и случае поступления
        patient = ClinicalSchedulingService._get_patient_from_assignment(assignment)
        department = ClinicalSchedulingService._get_department_from_assignment(assignment)
        encounter = ClinicalSchedulingService._get_encounter_from_assignment(assignment)

        
        if not patient:
            raise ValueError("Не удалось определить пациента для назначения")
        
        if not department:
            # Если не удалось определить отделение, используем приемное отделение
            try:
                department = Department.objects.filter(slug='admission').first()
                if not department:
                    # Если нет приемного отделения, используем первое доступное
                    department = Department.objects.first()
                if not department:
                    raise ValueError("Не удалось определить отделение для назначения")
            except Exception as e:
                raise ValueError("Не удалось определить отделение для назначения")

        
        if hasattr(assignment, 'medication'):
            return ClinicalSchedulingService._create_medication_schedule(
                assignment, patient, department, encounter, start_date, first_time, times_per_day, duration_days
            )
        elif hasattr(assignment, 'lab_test'):
            return ClinicalSchedulingService._create_lab_test_schedule(
                assignment, patient, department, encounter, start_date, first_time
            )
        elif hasattr(assignment, 'instrumental_procedure'):
            return ClinicalSchedulingService._create_procedure_schedule(
                assignment, patient, department, encounter, start_date, first_time
            )
        return []
    
    @staticmethod
    def _get_patient_from_assignment(assignment):
        """Получает пациента из назначения"""
        
        try:
            # Проверяем прямые атрибуты
            if hasattr(assignment, 'patient'):
                return assignment.patient
            
            # Проверяем через treatment_plan
            if hasattr(assignment, 'treatment_plan'):
                
                # Сначала проверяем patient_department_status
                if hasattr(assignment.treatment_plan, 'patient_department_status') and assignment.treatment_plan.patient_department_status:
                    try:
                        patient = assignment.treatment_plan.patient_department_status.patient
                        return patient
                    except Exception:
                        pass
                
                # Затем проверяем encounter
                if hasattr(assignment.treatment_plan, 'encounter') and assignment.treatment_plan.encounter:
                    try:
                        patient = assignment.treatment_plan.encounter.patient
                        return patient
                    except Exception:
                        pass
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.treatment_plan, 'owner') and assignment.treatment_plan.owner:
                    try:
                        if hasattr(assignment.treatment_plan.owner, 'patient'):
                            patient = assignment.treatment_plan.owner.patient
                            return patient
                        elif hasattr(assignment.treatment_plan.owner, 'get_patient'):
                            patient = assignment.treatment_plan.owner.get_patient()
                            return patient
                    except Exception:
                        pass
            
            # Проверяем через examination_plan
            elif hasattr(assignment, 'examination_plan'):
                
                # Сначала проверяем patient_department_status
                if hasattr(assignment.examination_plan, 'patient_department_status') and assignment.examination_plan.patient_department_status:
                    try:
                        patient = assignment.examination_plan.patient_department_status.patient
                        return patient
                    except Exception:
                        pass
                
                # Затем проверяем encounter
                if hasattr(assignment.examination_plan, 'encounter') and assignment.examination_plan.encounter:
                    try:
                        patient = assignment.examination_plan.encounter.patient
                        return patient
                    except Exception:
                        pass
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.examination_plan, 'owner') and assignment.examination_plan.owner:
                    try:
                        if hasattr(assignment.examination_plan.owner, 'patient'):
                            patient = assignment.examination_plan.owner.patient
                            return patient
                        elif hasattr(assignment.examination_plan.owner, 'get_patient'):
                            patient = assignment.examination_plan.owner.get_patient()
                            return patient
                    except Exception:
                        pass

                
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_department_from_assignment(assignment):
        """Получает отделение из назначения"""

        
        try:
            if hasattr(assignment, 'treatment_plan'):
                
                if hasattr(assignment.treatment_plan, 'patient_department_status') and assignment.treatment_plan.patient_department_status:
                    try:
                        department = assignment.treatment_plan.patient_department_status.department
                        return department
                    except Exception:
                        pass
                
                elif hasattr(assignment.treatment_plan, 'encounter') and assignment.treatment_plan.encounter:
                    try:
                        # Пытаемся получить отделение из случая поступления
                        encounter = assignment.treatment_plan.encounter

                        
                        # Проверяем через department_transfer_records (PatientDepartmentStatus)
                        if hasattr(encounter, 'department_transfer_records'):
                            department_records = encounter.department_transfer_records.filter(
                                status__in=['pending', 'accepted']
                            ).order_by('-admission_date')
                            
                            if department_records.exists():
                                department = department_records.first().department
                                return department
                        
                        # Проверяем через transfer_to_department
                        if hasattr(encounter, 'transfer_to_department') and encounter.transfer_to_department:
                            department = encounter.transfer_to_department
                            return department
                        
                        # Проверяем через source_encounter в PatientDepartmentStatus
                        from departments.models import PatientDepartmentStatus
                        try:
                            patient_status = PatientDepartmentStatus.objects.filter(
                                patient=encounter.patient,
                                status__in=['pending', 'accepted']
                            ).order_by('-admission_date').first()
                            
                            if patient_status:
                                department = patient_status.department
                                return department
                        except Exception:
                            pass
                            
                    except Exception:
                        pass
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.treatment_plan, 'owner') and assignment.treatment_plan.owner:
                    try:
                        if hasattr(assignment.treatment_plan.owner, 'department'):
                            department = assignment.treatment_plan.owner.department
                            return department
                        elif hasattr(assignment.treatment_plan.owner, 'get_department'):
                            department = assignment.treatment_plan.owner.get_department()
                            return department
                    except Exception:
                        pass
            
            elif hasattr(assignment, 'examination_plan'):
                
                if hasattr(assignment.examination_plan, 'patient_department_status') and assignment.examination_plan.patient_department_status:
                    try:
                        department = assignment.examination_plan.patient_department_status.department
                        return department
                    except Exception:
                        pass
                
                elif hasattr(assignment.examination_plan, 'encounter') and assignment.examination_plan.encounter:
                    try:
                        # Пытаемся получить отделение из случая поступления
                        encounter = assignment.examination_plan.encounter

                        
                        # Проверяем через department_transfer_records (PatientDepartmentStatus)
                        if hasattr(encounter, 'department_transfer_records'):
                            department_records = encounter.department_transfer_records.filter(
                                status__in=['pending', 'accepted']
                            ).order_by('-admission_date')
                            
                            if department_records.exists():
                                department = department_records.first().department
                                return department
                        
                        # Проверяем через transfer_to_department
                        if hasattr(encounter, 'transfer_to_department') and encounter.transfer_to_department:
                            department = encounter.transfer_to_department
                            return department
                        
                        # Проверяем через source_encounter в PatientDepartmentStatus
                        from departments.models import PatientDepartmentStatus
                        try:
                            patient_status = PatientDepartmentStatus.objects.filter(
                                patient=encounter.patient,
                                status__in=['pending', 'accepted']
                            ).order_by('-admission_date').first()
                            
                            if patient_status:
                                department = patient_status.department
                                return department
                        except Exception:
                            pass
                            
                    except Exception:
                        pass
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.examination_plan, 'owner') and assignment.examination_plan.owner:
                    try:
                        if hasattr(assignment.examination_plan.owner, 'department'):
                            department = assignment.examination_plan.owner.department
                            return department
                        elif hasattr(assignment.examination_plan.owner, 'get_department'):
                            department = assignment.examination_plan.owner.get_department()
                            return department
                    except Exception:
                        pass
            

                
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_encounter_from_assignment(assignment):
        """Получает случай поступления из назначения"""
        try:
            if hasattr(assignment, 'treatment_plan'):
                if hasattr(assignment.treatment_plan, 'encounter'):
                    return assignment.treatment_plan.encounter
            elif hasattr(assignment, 'examination_plan'):
                if hasattr(assignment.examination_plan, 'encounter'):
                    return assignment.examination_plan.encounter
        except Exception:
            pass
        return None
    
    @staticmethod
    def _create_medication_schedule(assignment, patient, department, encounter, start_date, first_time, times_per_day, duration_days):
        """Создает расписание для лекарства"""
        schedules = []
        current_date = start_date
        
        for day in range(duration_days):
            day_schedules = ClinicalSchedulingService._create_day_schedule(
                assignment, patient, department, encounter, current_date, first_time, times_per_day
            )
            schedules.extend(day_schedules)
            current_date += timedelta(days=1)
        
        return schedules
    
    @staticmethod
    def _create_day_schedule(assignment, patient, department, encounter, date, first_time, times_per_day):
        """Создает расписание на один день с правильным распределением по 24 часам"""
        schedules = []
        content_type = ContentType.objects.get_for_model(assignment)
        
        if times_per_day == 1:
            schedules.append(ScheduledAppointment.objects.create(
                content_type=content_type,
                object_id=assignment.id,
                patient=patient,
                created_department=department,
                encounter=encounter,
                scheduled_date=date,
                scheduled_time=first_time
            ))
        else:
            # Вычисляем интервал в часах (24 часа / количество приемов)
            interval_hours = 24 // times_per_day
            
            # Создаем назначения для всех приемов
            for i in range(times_per_day):
                # Вычисляем время для каждого приема
                total_hours_from_start = i * interval_hours
                
                # Вычисляем новое время с учетом переноса на следующий день
                start_hour = first_time.hour
                start_minute = first_time.minute
                
                new_hour = (start_hour + total_hours_from_start) % 24
                new_time = time(new_hour, start_minute)
                
                # Определяем дату: если время перешло через полночь, добавляем дни
                days_to_add = (start_hour + total_hours_from_start) // 24
                appointment_date = date + timedelta(days=days_to_add)
                
                schedules.append(ScheduledAppointment.objects.create(
                    content_type=content_type,
                    object_id=assignment.id,
                    patient=patient,
                    created_department=department,
                    encounter=encounter,
                    scheduled_date=appointment_date,
                    scheduled_time=new_time
                ))
        
        return schedules
    
    @staticmethod
    def _add_hours_to_time(time_obj, hours):
        """Добавляет часы к времени, учитывая переход через полночь"""
        total_minutes = time_obj.hour * 60 + time_obj.minute + (hours * 60)
        total_minutes = total_minutes % (24 * 60)
        new_hours = total_minutes // 60
        new_minutes = total_minutes % 60
        return time(new_hours, new_minutes)
    
    @staticmethod
    def _create_lab_test_schedule(assignment, patient, department, encounter, start_date, first_time):
        """Создает расписание для лабораторного исследования"""
        content_type = ContentType.objects.get_for_model(assignment)
        return [ScheduledAppointment.objects.create(
            content_type=content_type,
            object_id=assignment.id,
            patient=patient,
            created_department=department,
            encounter=encounter,
            scheduled_date=start_date,
            scheduled_time=first_time
        )]
    
    @staticmethod
    def _create_procedure_schedule(assignment, patient, department, encounter, start_date, first_time):
        """Создает расписание для инструментального исследования"""
        content_type = ContentType.objects.get_for_model(assignment)
        return [ScheduledAppointment.objects.create(
            content_type=content_type,
            object_id=assignment.id,
            patient=patient,
            created_department=department,
            encounter=encounter,
            scheduled_date=start_date,
            scheduled_time=first_time
        )]
    
    @staticmethod
    def get_today_schedule(patient=None, department=None, user=None):
        """Получает расписание на сегодня"""
        today = timezone.now().date()
        queryset = ScheduledAppointment.objects.filter(
            scheduled_date=today
        ).select_related('executed_by', 'rejected_by', 'patient', 'created_department')
        
        if patient:
            queryset = queryset.filter(patient=patient)
        
        if department:
            queryset = queryset.filter(created_department=department)
        
        # Фильтруем по правам доступа пользователя
        if user and not user.is_superuser:
            try:
                user_department = user.department
                # Показываем все назначения, но редактировать можно только из своего отделения
                pass
            except:
                pass
        
        return queryset.order_by('scheduled_time')
    
    @staticmethod
    def get_overdue_appointments(patient=None, department=None, user=None):
        """Получает просроченные назначения"""
        today = timezone.now().date()
        queryset = ScheduledAppointment.objects.filter(
            scheduled_date__lt=today,
            execution_status__in=['scheduled', 'partial']
        ).select_related('executed_by', 'patient', 'created_department')
        
        if patient:
            queryset = queryset.filter(patient=patient)
        
        if department:
            queryset = queryset.filter(created_department=department)
        
        return queryset.order_by('-scheduled_date', 'scheduled_time')
    
    @staticmethod
    def get_patient_schedule(patient, start_date=None, end_date=None):
        """Получает расписание пациента за период"""
        queryset = ScheduledAppointment.objects.filter(patient=patient).exclude(
            execution_status='canceled'  # Исключаем отмененные назначения
        )
        
        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(scheduled_date__lte=end_date)
        
        return queryset.select_related(
            'executed_by', 'rejected_by', 'created_department'
        ).order_by('-scheduled_date', 'scheduled_time')
    
    @staticmethod
    def create_schedule_for_recommendation(recommendation, patient, department, start_date, first_time, times_per_day, duration_days, encounter=None):
        """
        Создает расписание для рекомендации
        
        Args:
            recommendation: Рекомендация (TreatmentRecommendation)
            patient: Пациент
            department: Отделение
            start_date: Дата начала
            first_time: Время первого выполнения
            times_per_day: Количество раз в день
            duration_days: Длительность в днях
            encounter: Случай поступления (опционально)
        """
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(recommendation)
        schedules = []
        
        # Создаем расписание на каждый день
        for day in range(duration_days):
            appointment_date = start_date + timedelta(days=day)
            
            # Создаем записи на каждый прием в день
            for time_index in range(times_per_day):
                # Вычисляем время для текущего приема
                if time_index == 0:
                    appointment_time = first_time
                else:
                    # Распределяем приемы равномерно в течение дня
                    hours_between = 24 // times_per_day
                    appointment_time = ClinicalSchedulingService._add_hours_to_time(
                        first_time, hours_between * time_index
                    )
                
                # Создаем запланированное событие
                schedule = ScheduledAppointment.objects.create(
                    content_type=content_type,
                    object_id=recommendation.id,
                    patient=patient,
                    created_department=department,
                    encounter=encounter,
                    scheduled_date=appointment_date,
                    scheduled_time=appointment_time
                )
                schedules.append(schedule)
        
        return schedules