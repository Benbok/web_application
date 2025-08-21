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
        print(f"🔧 ClinicalSchedulingService.create_schedule_for_assignment вызван для {assignment}")
        print(f"📝 Тип назначения: {type(assignment).__name__}")
        
        if not start_date:
            start_date = timezone.now().date()
        if not first_time:
            first_time = time(9, 0)
        if not times_per_day:
            times_per_day = 1
        if not duration_days:
            duration_days = 7
        
        print(f"📅 Параметры: start_date={start_date}, first_time={first_time}, times_per_day={times_per_day}, duration_days={duration_days}")
        
        # Получаем информацию о пациенте, отделении и случае поступления
        patient = ClinicalSchedulingService._get_patient_from_assignment(assignment)
        department = ClinicalSchedulingService._get_department_from_assignment(assignment)
        encounter = ClinicalSchedulingService._get_encounter_from_assignment(assignment)
        
        print(f"👤 Пациент: {patient}")
        print(f"🏥 Отделение: {department}")
        print(f"📋 Случай поступления: {encounter}")
        
        if not patient:
            print("❌ Не удалось определить пациента для назначения")
            raise ValueError("Не удалось определить пациента для назначения")
        
        if not department:
            print("⚠️ Не удалось определить отделение для назначения, используем приемное отделение")
            # Если не удалось определить отделение, используем приемное отделение
            try:
                department = Department.objects.filter(slug='admission').first()
                if not department:
                    # Если нет приемного отделения, используем первое доступное
                    department = Department.objects.first()
                if department:
                    print(f"✅ Использую отделение по умолчанию: {department}")
                else:
                    print("❌ Не удалось найти ни одного отделения")
                    raise ValueError("Не удалось определить отделение для назначения")
            except Exception as e:
                print(f"❌ Ошибка при поиске отделения по умолчанию: {e}")
                raise ValueError("Не удалось определить отделение для назначения")
        
        print(f"🔍 Проверяю атрибуты назначения: {[attr for attr in dir(assignment) if not attr.startswith('_')]}")
        
        if hasattr(assignment, 'medication'):
            print("💊 Создаю расписание для лекарства")
            return ClinicalSchedulingService._create_medication_schedule(
                assignment, patient, department, encounter, start_date, first_time, times_per_day, duration_days
            )
        elif hasattr(assignment, 'lab_test'):
            print("🧪 Создаю расписание для лабораторного теста")
            return ClinicalSchedulingService._create_lab_test_schedule(
                assignment, patient, department, encounter, start_date, first_time
            )
        elif hasattr(assignment, 'instrumental_procedure'):
            print("🔬 Создаю расписание для инструментального исследования")
            return ClinicalSchedulingService._create_procedure_schedule(
                assignment, patient, department, encounter, start_date, first_time
            )
        else:
            print("⚠️ Неизвестный тип назначения")
        return []
    
    @staticmethod
    def _get_patient_from_assignment(assignment):
        """Получает пациента из назначения"""
        print(f"🔍 _get_patient_from_assignment: {assignment}")
        print(f"📝 Тип: {type(assignment).__name__}")
        
        try:
            # Проверяем прямые атрибуты
            if hasattr(assignment, 'patient'):
                print(f"✅ Найден прямой атрибут patient: {assignment.patient}")
                return assignment.patient
            
            # Проверяем через treatment_plan
            if hasattr(assignment, 'treatment_plan'):
                print(f"🔗 Найден treatment_plan: {assignment.treatment_plan}")
                
                # Сначала проверяем patient_department_status
                if hasattr(assignment.treatment_plan, 'patient_department_status') and assignment.treatment_plan.patient_department_status:
                    try:
                        patient = assignment.treatment_plan.patient_department_status.patient
                        print(f"✅ Пациент через patient_department_status: {patient}")
                        return patient
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении пациента через patient_department_status: {e}")
                
                # Затем проверяем encounter
                if hasattr(assignment.treatment_plan, 'encounter') and assignment.treatment_plan.encounter:
                    try:
                        patient = assignment.treatment_plan.encounter.patient
                        print(f"✅ Пациент через encounter: {patient}")
                        return patient
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении пациента через encounter: {e}")
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.treatment_plan, 'owner') and assignment.treatment_plan.owner:
                    try:
                        if hasattr(assignment.treatment_plan.owner, 'patient'):
                            patient = assignment.treatment_plan.owner.patient
                            print(f"✅ Пациент через owner.patient: {patient}")
                            return patient
                        elif hasattr(assignment.treatment_plan.owner, 'get_patient'):
                            patient = assignment.treatment_plan.owner.get_patient()
                            print(f"✅ Пациент через owner.get_patient(): {patient}")
                            return patient
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении пациента через owner: {e}")
            
            # Проверяем через examination_plan
            elif hasattr(assignment, 'examination_plan'):
                print(f"🔗 Найден examination_plan: {assignment.examination_plan}")
                
                # Сначала проверяем patient_department_status
                if hasattr(assignment.examination_plan, 'patient_department_status') and assignment.examination_plan.patient_department_status:
                    try:
                        patient = assignment.examination_plan.patient_department_status.patient
                        print(f"✅ Пациент через patient_department_status: {patient}")
                        return patient
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении пациента через patient_department_status: {e}")
                
                # Затем проверяем encounter
                if hasattr(assignment.examination_plan, 'encounter') and assignment.examination_plan.encounter:
                    try:
                        patient = assignment.examination_plan.encounter.patient
                        print(f"✅ Пациент через encounter: {patient}")
                        return patient
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении пациента через encounter: {e}")
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.examination_plan, 'owner') and assignment.examination_plan.owner:
                    try:
                        if hasattr(assignment.examination_plan.owner, 'patient'):
                            patient = assignment.examination_plan.owner.patient
                            print(f"✅ Пациент через owner.patient: {patient}")
                            return patient
                        elif hasattr(assignment.examination_plan.owner, 'get_patient'):
                            patient = assignment.examination_plan.owner.get_patient()
                            print(f"✅ Пациент через owner.get_patient(): {patient}")
                            return patient
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении пациента через owner: {e}")
            
            else:
                print("❌ Не найдено подходящих атрибутов для получения пациента")
                print(f"🔍 Доступные атрибуты: {[attr for attr in dir(assignment) if not attr.startswith('_')]}")
                
        except Exception as e:
            print(f"❌ Ошибка при получении пациента: {e}")
            import traceback
            traceback.print_exc()
        return None
    
    @staticmethod
    def _get_department_from_assignment(assignment):
        """Получает отделение из назначения"""
        print(f"🏥 _get_department_from_assignment: {assignment}")
        
        try:
            if hasattr(assignment, 'treatment_plan'):
                print(f"🔗 Найден treatment_plan: {assignment.treatment_plan}")
                
                if hasattr(assignment.treatment_plan, 'patient_department_status') and assignment.treatment_plan.patient_department_status:
                    try:
                        department = assignment.treatment_plan.patient_department_status.department
                        print(f"✅ Отделение через patient_department_status: {department}")
                        return department
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении отделения через patient_department_status: {e}")
                
                elif hasattr(assignment.treatment_plan, 'encounter') and assignment.treatment_plan.encounter:
                    try:
                        # Пытаемся получить отделение из случая поступления
                        encounter = assignment.treatment_plan.encounter
                        print(f"🔍 Проверяю encounter: {encounter}")
                        
                        # Проверяем через department_transfer_records (PatientDepartmentStatus)
                        if hasattr(encounter, 'department_transfer_records'):
                            department_records = encounter.department_transfer_records.filter(
                                status__in=['pending', 'accepted']
                            ).order_by('-admission_date')
                            
                            if department_records.exists():
                                department = department_records.first().department
                                print(f"✅ Отделение через department_transfer_records: {department}")
                                return department
                        
                        # Проверяем через transfer_to_department
                        if hasattr(encounter, 'transfer_to_department') and encounter.transfer_to_department:
                            department = encounter.transfer_to_department
                            print(f"✅ Отделение через transfer_to_department: {department}")
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
                                print(f"✅ Отделение через PatientDepartmentStatus: {department}")
                                return department
                        except Exception as e:
                            print(f"⚠️ Ошибка при получении отделения через PatientDepartmentStatus: {e}")
                            
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении отделения через encounter: {e}")
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.treatment_plan, 'owner') and assignment.treatment_plan.owner:
                    try:
                        if hasattr(assignment.treatment_plan.owner, 'department'):
                            department = assignment.treatment_plan.owner.department
                            print(f"✅ Отделение через owner.department: {department}")
                            return department
                        elif hasattr(assignment.treatment_plan.owner, 'get_department'):
                            department = assignment.treatment_plan.owner.get_department()
                            print(f"✅ Отделение через owner.get_department(): {department}")
                            return department
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении отделения через owner: {e}")
            
            elif hasattr(assignment, 'examination_plan'):
                print(f"🔗 Найден examination_plan: {assignment.examination_plan}")
                
                if hasattr(assignment.examination_plan, 'patient_department_status') and assignment.examination_plan.patient_department_status:
                    try:
                        department = assignment.examination_plan.patient_department_status.department
                        print(f"✅ Отделение через patient_department_status: {department}")
                        return department
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении отделения через patient_department_status: {e}")
                
                elif hasattr(assignment.examination_plan, 'encounter') and assignment.examination_plan.encounter:
                    try:
                        # Пытаемся получить отделение из случая поступления
                        encounter = assignment.examination_plan.encounter
                        print(f"🔍 Проверяю encounter: {encounter}")
                        
                        # Проверяем через department_transfer_records (PatientDepartmentStatus)
                        if hasattr(encounter, 'department_transfer_records'):
                            department_records = encounter.department_transfer_records.filter(
                                status__in=['pending', 'accepted']
                            ).order_by('-admission_date')
                            
                            if department_records.exists():
                                department = department_records.first().department
                                print(f"✅ Отделение через department_transfer_records: {department}")
                                return department
                        
                        # Проверяем через transfer_to_department
                        if hasattr(encounter, 'transfer_to_department') and encounter.transfer_to_department:
                            department = encounter.transfer_to_department
                            print(f"✅ Отделение через transfer_to_department: {department}")
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
                                print(f"✅ Отделение через PatientDepartmentStatus: {department}")
                                return department
                        except Exception as e:
                            print(f"⚠️ Ошибка при получении отделения через PatientDepartmentStatus: {e}")
                            
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении отделения через encounter: {e}")
                
                # Проверяем owner (GenericForeignKey)
                if hasattr(assignment.examination_plan, 'owner') and assignment.examination_plan.owner:
                    try:
                        if hasattr(assignment.examination_plan.owner, 'department'):
                            department = assignment.examination_plan.owner.department
                            print(f"✅ Отделение через owner.department: {department}")
                            return department
                        elif hasattr(assignment.examination_plan.owner, 'get_department'):
                            department = assignment.examination_plan.owner.get_department()
                            print(f"✅ Отделение через owner.get_department(): {department}")
                            return department
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении отделения через owner: {e}")
            
            else:
                print("❌ Не найдено подходящих атрибутов для получения отделения")
                
        except Exception as e:
            print(f"❌ Ошибка при получении отделения: {e}")
            import traceback
            traceback.print_exc()
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
        """Создает расписание на один день"""
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
            interval_hours = 24 // times_per_day
            current_time = first_time
            
            # Первое назначение дня
            schedules.append(ScheduledAppointment.objects.create(
                content_type=content_type,
                object_id=assignment.id,
                patient=patient,
                created_department=department,
                encounter=encounter,
                scheduled_date=date,
                scheduled_time=current_time
            ))
            
            # Остальные назначения дня
            for i in range(1, times_per_day):
                current_time = ClinicalSchedulingService._add_hours_to_time(current_time, interval_hours)
                schedules.append(ScheduledAppointment.objects.create(
                    content_type=content_type,
                    object_id=assignment.id,
                    patient=patient,
                    created_department=department,
                    encounter=encounter,
                    scheduled_date=date,
                    scheduled_time=current_time
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
        
        return queryset.order_by('scheduled_date', 'scheduled_time')
    
    @staticmethod
    def get_patient_schedule(patient, start_date=None, end_date=None):
        """Получает расписание пациента за период"""
        queryset = ScheduledAppointment.objects.filter(patient=patient)
        
        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(scheduled_date__lte=end_date)
        
        return queryset.select_related(
            'executed_by', 'rejected_by', 'created_department'
        ).order_by('scheduled_date', 'scheduled_time')