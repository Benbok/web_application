from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta, date
import random
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

# Импорты моделей
from patients.models import Patient, PatientContact, PatientAddress, PatientDocument
from profiles.models import DoctorProfile
from departments.models import Department, PatientDepartmentStatus
from encounters.models import Encounter
from appointments.models import Schedule, AppointmentEvent
from pharmacy.models import Medication, DosingRule
from lab_tests.models import LabTestDefinition, LabTestResult
from instrumental_procedures.models import InstrumentalProcedureDefinition, InstrumentalProcedureResult
from documents.models import DocumentType, ClinicalDocument, DocumentTemplate
# Импорты treatment_assignments удалены - больше не нужны
from newborns.models import NewbornProfile


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными'

    def handle(self, *args, **options):
        self.stdout.write('Начинаю заполнение базы данных тестовыми данными...')
        
        # Создаем пользователей и врачей
        users = self.create_users_and_doctors()
        
        # Создаем отделения
        departments = self.create_departments()
        
        # Создаем пациентов
        patients = self.create_patients()
        
        # Создаем случаи обращений
        encounters = self.create_encounters(patients, users, departments)
        
        # Создаем расписания и записи
        self.create_appointments(users, patients)
        
        # Создаем препараты и правила дозирования
        medications = self.create_medications()
        
        # Создаем лабораторные исследования
        lab_tests = self.create_lab_tests()
        
        # Создаем инструментальные исследования
        instrumental_procedures = self.create_instrumental_procedures()
        
        # Создаем типы документов
        document_types = self.create_document_types(departments)
        
        # Создаем назначения
        # self.create_treatment_assignments(patients, users, medications, lab_tests, instrumental_procedures, encounters)  # УДАЛЕНО
        
        # Создаем документы
        self.create_documents(patients, users, document_types, encounters)
        
        self.stdout.write(
            self.style.SUCCESS('База данных успешно заполнена тестовыми данными!')
        )

    def create_users_and_doctors(self):
        """Создает пользователей и профили врачей"""
        users_data = [
            {
                'username': 'dr_ivanov',
                'email': 'ivanov@hospital.ru',
                'first_name': 'Иван',
                'last_name': 'Иванов',
                'specialization': 'Терапевт',
                'position': 'Врач-терапевт'
            },
            {
                'username': 'dr_petrov',
                'email': 'petrov@hospital.ru',
                'first_name': 'Петр',
                'last_name': 'Петров',
                'specialization': 'Хирург',
                'position': 'Врач-хирург'
            },
            {
                'username': 'dr_sidorov',
                'email': 'sidorov@hospital.ru',
                'first_name': 'Алексей',
                'last_name': 'Сидоров',
                'specialization': 'Кардиолог',
                'position': 'Врач-кардиолог'
            },
            {
                'username': 'dr_kozlov',
                'email': 'kozlov@hospital.ru',
                'first_name': 'Мария',
                'last_name': 'Козлова',
                'specialization': 'Педиатр',
                'position': 'Врач-педиатр'
            }
        ]
        
        users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_staff': True
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
            
            profile, created = DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f"{user_data['last_name']} {user_data['first_name']}",
                    'specialization': user_data['specialization'],
                    'position': user_data['position'],
                    'employment_date': date(2020, 1, 1)
                }
            )
            users.append(user)
        
        self.stdout.write(f'Создано {len(users)} пользователей и врачей')
        return users

    def create_departments(self):
        """Создает отделения"""
        departments_data = [
            {'name': 'Терапевтическое отделение', 'slug': 'therapy'},
            {'name': 'Хирургическое отделение', 'slug': 'surgery'},
            {'name': 'Кардиологическое отделение', 'slug': 'cardiology'},
            {'name': 'Педиатрическое отделение', 'slug': 'pediatrics'},
            {'name': 'Реанимационное отделение', 'slug': 'icu'},
            {'name': 'Отделение новорожденных', 'slug': 'neonatal'}
        ]
        
        departments = []
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                slug=dept_data['slug'],
                defaults={'name': dept_data['name']}
            )
            departments.append(dept)
        
        self.stdout.write(f'Создано {len(departments)} отделений')
        return departments

    def create_patients(self):
        """Создает пациентов"""
        patients_data = [
            {
                'last_name': 'Смирнов', 'first_name': 'Александр', 'middle_name': 'Иванович',
                'birth_date': date(1985, 3, 15), 'gender': 'male', 'patient_type': 'adult'
            },
            {
                'last_name': 'Кузнецова', 'first_name': 'Елена', 'middle_name': 'Петровна',
                'birth_date': date(1990, 7, 22), 'gender': 'female', 'patient_type': 'adult'
            },
            {
                'last_name': 'Морозов', 'first_name': 'Дмитрий', 'middle_name': 'Сергеевич',
                'birth_date': date(1978, 11, 8), 'gender': 'male', 'patient_type': 'adult'
            },
            {
                'last_name': 'Волкова', 'first_name': 'Анна', 'middle_name': 'Александровна',
                'birth_date': date(1995, 4, 12), 'gender': 'female', 'patient_type': 'adult'
            },
            {
                'last_name': 'Лебедев', 'first_name': 'Михаил', 'middle_name': 'Дмитриевич',
                'birth_date': date(2015, 9, 3), 'gender': 'male', 'patient_type': 'child'
            },
            {
                'last_name': 'Соколова', 'first_name': 'Ольга', 'middle_name': 'Владимировна',
                'birth_date': date(2024, 1, 15), 'gender': 'female', 'patient_type': 'newborn'
            }
        ]
        
        patients = []
        for patient_data in patients_data:
            patient, created = Patient.objects.get_or_create(
                last_name=patient_data['last_name'],
                first_name=patient_data['first_name'],
                birth_date=patient_data['birth_date'],
                defaults={
                    'middle_name': patient_data['middle_name'],
                    'gender': patient_data['gender'],
                    'patient_type': patient_data['patient_type']
                }
            )
            
            # Создаем контактную информацию
            if created:
                PatientContact.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'phone': f'+7{random.randint(9000000000, 9999999999)}',
                        'email': f"{patient_data['first_name'].lower()}.{patient_data['last_name'].lower()}@example.com"
                    }
                )
                
                PatientAddress.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'registration_address': f'г. Москва, ул. Примерная, д. {random.randint(1, 100)}',
                        'residential_address': f'г. Москва, ул. Примерная, д. {random.randint(1, 100)}'
                    }
                )
                
                PatientDocument.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'passport_series': f'{random.randint(1000, 9999)}',
                        'passport_number': f'{random.randint(100000, 999999)}',
                        'snils': f'{random.randint(10000000000, 99999999999)}',
                        'insurance_policy_number': f'{random.randint(1000000000000000, 9999999999999999)}'
                    }
                )
            
            patients.append(patient)
        
        # Создаем профиль новорожденного для последнего пациента
        if patients[-1].patient_type == 'newborn':
                            NewbornProfile.objects.get_or_create(
                    patient=patients[-1],
                    defaults={
                        'birth_time': datetime.now().time(),
                        'gestational_age_weeks': 38,
                        'gestational_age_days': 2,
                        'birth_weight_grams': 3200,
                        'birth_height_cm': 50,
                        'head_circumference_cm': Decimal('34.5'),
                        'apgar_score_1_min': 8,
                        'apgar_score_5_min': 9,
                        'apgar_score_10_min': 9
                    }
                )
        
        self.stdout.write(f'Создано {len(patients)} пациентов')
        return patients

    def create_encounters(self, patients, users, departments):
        """Создает случаи обращений"""
        encounters = []
        for i, patient in enumerate(patients):
            # Создаем 1-2 случая обращения для каждого пациента
            for j in range(random.randint(1, 2)):
                encounter = Encounter.objects.create(
                    patient=patient,
                    doctor=random.choice(users),
                    date_start=timezone.now() - timedelta(days=random.randint(1, 30)),
                    date_end=timezone.now() - timedelta(days=random.randint(0, 29)) if random.choice([True, False]) else None,
                    is_active=random.choice([True, False]),
                    outcome=random.choice(['consultation_end', 'transferred']) if random.choice([True, False]) else None,
                    transfer_to_department=random.choice(departments) if random.choice([True, False]) else None
                )
                encounters.append(encounter)
        
        self.stdout.write(f'Создано {len(encounters)} случаев обращений')
        return encounters

    def create_appointments(self, users, patients):
        """Создает расписания и записи на прием"""
        # Создаем расписания для врачей
        schedules = []
        for user in users:
            if hasattr(user, 'doctor_profile'):
                schedule = Schedule.objects.create(
                    doctor=user,
                    start_time=datetime.strptime('09:00', '%H:%M').time(),
                    end_time=datetime.strptime('17:00', '%H:%M').time(),
                    duration=30
                )
                schedules.append(schedule)
        
        # Создаем записи на прием
        appointments = []
        for _ in range(20):
            patient = random.choice(patients)
            schedule = random.choice(schedules) if schedules else None
            
            start_time = timezone.now() + timedelta(days=random.randint(1, 30), hours=random.randint(9, 16))
            end_time = start_time + timedelta(minutes=30)
            
            appointment = AppointmentEvent.objects.create(
                schedule=schedule,
                patient=patient,
                start=start_time,
                end=end_time,
                status=random.choice(['scheduled', 'completed', 'canceled']),
                notes=f'Заметка к записи {random.randint(1, 100)}' if random.choice([True, False]) else ''
            )
            appointments.append(appointment)
        
        self.stdout.write(f'Создано {len(schedules)} расписаний и {len(appointments)} записей')

    def create_medications(self):
        """Создает препараты и правила дозирования"""
        medications_data = [
            {'name': 'Парацетамол', 'form': 'таблетки'},
            {'name': 'Ибупрофен', 'form': 'таблетки'},
            {'name': 'Амоксициллин', 'form': 'капсулы'},
            {'name': 'Аспирин', 'form': 'таблетки'},
            {'name': 'Омепразол', 'form': 'капсулы'},
            {'name': 'Метформин', 'form': 'таблетки'},
            {'name': 'Аторвастатин', 'form': 'таблетки'},
            {'name': 'Лозартан', 'form': 'таблетки'}
        ]
        
        medications = []
        for med_data in medications_data:
            medication, created = Medication.objects.get_or_create(
                name=med_data['name'],
                defaults={
                    'form': med_data['form'],
                    'description': f'Описание препарата {med_data["name"]}'
                }
            )
            medications.append(medication)
            
            # Создаем правила дозирования
            if created:
                DosingRule.objects.create(
                    medication=medication,
                    name='Стандартная дозировка для взрослых',
                    route_of_administration='oral',
                    min_age_days=6570,  # 18 лет
                    max_age_days=36500,  # 100 лет
                    min_weight_kg=Decimal('50.00'),
                    max_weight_kg=Decimal('120.00'),
                    is_loading_dose=False,
                    dosage_value=Decimal('1.00'),
                    dosage_unit='таблетка',
                    frequency_text='3 раза в сутки, каждые 8 часов',
                    max_daily_dosage_text='3.00',
                    notes='Принимать после еды'
                )
        
        self.stdout.write(f'Создано {len(medications)} препаратов с правилами дозирования')
        return medications

    def create_lab_tests(self):
        """Создает лабораторные исследования"""
        lab_tests_data = [
            {'name': 'Общий анализ крови', 'description': 'Базовый анализ крови'},
            {'name': 'Биохимический анализ крови', 'description': 'Анализ биохимических показателей'},
            {'name': 'Общий анализ мочи', 'description': 'Базовый анализ мочи'},
            {'name': 'Анализ на глюкозу', 'description': 'Определение уровня глюкозы в крови'},
            {'name': 'Анализ на холестерин', 'description': 'Определение уровня холестерина'},
            {'name': 'Анализ на гормоны щитовидной железы', 'description': 'ТТГ, Т3, Т4'}
        ]
        
        lab_tests = []
        for test_data in lab_tests_data:
            lab_test, created = LabTestDefinition.objects.get_or_create(
                name=test_data['name'],
                defaults={
                    'description': test_data['description'],
                    'schema': {
                        'fields': [
                            {'name': 'result', 'type': 'text', 'label': 'Результат'},
                            {'name': 'normal_range', 'type': 'text', 'label': 'Нормальные значения'},
                            {'name': 'unit', 'type': 'text', 'label': 'Единицы измерения'}
                        ]
                    }
                }
            )
            lab_tests.append(lab_test)
        
        self.stdout.write(f'Создано {len(lab_tests)} лабораторных исследований')
        return lab_tests

    def create_instrumental_procedures(self):
        """Создает инструментальные исследования"""
        procedures_data = [
            {'name': 'ЭКГ', 'description': 'Электрокардиография'},
            {'name': 'УЗИ сердца', 'description': 'Ультразвуковое исследование сердца'},
            {'name': 'Рентген грудной клетки', 'description': 'Рентгенографическое исследование'},
            {'name': 'МРТ головного мозга', 'description': 'Магнитно-резонансная томография'},
            {'name': 'КТ легких', 'description': 'Компьютерная томография легких'},
            {'name': 'ФГДС', 'description': 'Фиброгастродуоденоскопия'}
        ]
        
        procedures = []
        for proc_data in procedures_data:
            procedure, created = InstrumentalProcedureDefinition.objects.get_or_create(
                name=proc_data['name'],
                defaults={
                    'description': proc_data['description'],
                    'schema': {
                        'fields': [
                            {'name': 'conclusion', 'type': 'textarea', 'label': 'Заключение'},
                            {'name': 'recommendations', 'type': 'textarea', 'label': 'Рекомендации'},
                            {'name': 'images_count', 'type': 'number', 'label': 'Количество снимков'}
                        ]
                    }
                }
            )
            procedures.append(procedure)
        
        self.stdout.write(f'Создано {len(procedures)} инструментальных исследований')
        return procedures

    def create_document_types(self, departments):
        """Создает типы документов"""
        document_types_data = [
            {
                'name': 'История болезни',
                'department': departments[0],  # Терапевтическое
                'schema': {
                    'fields': [
                        {'name': 'complaints', 'type': 'textarea', 'label': 'Жалобы'},
                        {'name': 'anamnesis', 'type': 'textarea', 'label': 'Анамнез'},
                        {'name': 'diagnosis', 'type': 'text', 'label': 'Диагноз'},
                        {'name': 'treatment_plan', 'type': 'textarea', 'label': 'План лечения'}
                    ]
                }
            },
            {
                'name': 'Выписной эпикриз',
                'department': departments[0],
                'schema': {
                    'fields': [
                        {'name': 'admission_diagnosis', 'type': 'text', 'label': 'Диагноз при поступлении'},
                        {'name': 'discharge_diagnosis', 'type': 'text', 'label': 'Диагноз при выписке'},
                        {'name': 'treatment_performed', 'type': 'textarea', 'label': 'Проведенное лечение'},
                        {'name': 'recommendations', 'type': 'textarea', 'label': 'Рекомендации'}
                    ]
                }
            },
            {
                'name': 'Операционный протокол',
                'department': departments[1],  # Хирургическое
                'schema': {
                    'fields': [
                        {'name': 'operation_name', 'type': 'text', 'label': 'Название операции'},
                        {'name': 'surgeon', 'type': 'text', 'label': 'Хирург'},
                        {'name': 'anesthesia_type', 'type': 'text', 'label': 'Тип анестезии'},
                        {'name': 'operation_description', 'type': 'textarea', 'label': 'Описание операции'}
                    ]
                }
            }
        ]
        
        document_types = []
        for doc_type_data in document_types_data:
            doc_type, created = DocumentType.objects.get_or_create(
                name=doc_type_data['name'],
                department=doc_type_data['department'],
                defaults={'schema': doc_type_data['schema']}
            )
            document_types.append(doc_type)
        
        self.stdout.write(f'Создано {len(document_types)} типов документов')
        return document_types

    # def create_treatment_assignments(self, patients, users, medications, lab_tests, instrumental_procedures, encounters):  # УДАЛЕНО
    #     """Создает назначения лечения"""
    #     encounter_content_type = ContentType.objects.get_for_model(Encounter)
    #     # Создаем назначения препаратов
    #     for _ in range(15):
    #         patient = random.choice(patients)
    #         medication = random.choice(medications)
    #         doctor = random.choice(users)
    #         encounter = random.choice(encounters) if encounters else None
    #         assignment = MedicationAssignment.objects.create(
    #             content_type=encounter_content_type if encounter else None,
    #             object_id=encounter.id if encounter else None,
    #             patient=patient,
    #             assigning_doctor=doctor,
    #             medication=medication,
    #             start_date=timezone.now() - timedelta(days=random.randint(1, 10)),
    #             end_date=timezone.now() + timedelta(days=random.randint(1, 14)) if random.choice([True, False]) else None,
    #             status=random.choice(['active', 'completed', 'canceled']),
    #             duration_days=random.randint(3, 14),
    #             patient_weight=Decimal(str(random.randint(50, 100)))
    #         )
    #     
    #     # Создаем общие назначения
    #     general_treatments = [
    #         'Постельный режим', 'Диета №5', 'Физиотерапия', 'ЛФК', 'Массаж',
    #         'Ингаляции', 'Компрессы', 'Прогулки на свежем воздухе'
    #     ]
    #     
    #     for _ in range(10):
    #         patient = random.choice(patients)
    #         doctor = random.choice(users)
    #         encounter = random.choice(encounters) if encounters else None
    #         
    #         GeneralTreatmentAssignment.objects.create(
    #             content_type=encounter_content_type if encounter else None,
    #             object_id=encounter.id if encounter else None,
    #             patient=patient,
    #             assigning_doctor=doctor,
    #             general_treatment=random.choice(general_treatments),
    #             start_date=timezone.now() - timedelta(days=random.randint(1, 10)),
    #             status=random.choice(['active', 'completed'])
    #         )
    #     
    #     # Создаем назначения лабораторных исследований
    #     for _ in range(12):
    #         patient = random.choice(patients)
    #         lab_test = random.choice(lab_tests)
    #         doctor = random.choice(users)
    #         encounter = random.choice(encounters) if encounters else None
    #         
    #         assignment = LabTestAssignment.objects.create(
    #             content_type=encounter_content_type if encounter else None,
    #             object_id=encounter.id if encounter else None,
    #             patient=patient,
    #             assigning_doctor=doctor,
    #             lab_test=lab_test,
    #             start_date=timezone.now() - timedelta(days=random.randint(1, 10)),
    #             status=random.choice(['active', 'completed'])
    #         )
    #         
    #         # Создаем результаты для некоторых назначений
    #         if random.choice([True, False]):
    #             LabTestResult.objects.create(
    #                 lab_test_assignment=assignment,
    #                 procedure_definition=lab_test,
    #                 author=doctor,
    #                 datetime_result=timezone.now() - timedelta(days=random.randint(1, 5)),
    #                 data={
    #                         'result': f'Результат {random.randint(1, 100)}',
    #                         'normal_range': '10-50',
    #                         'unit': 'мг/л'
    #                     }
    #                 )
    #     
    #     # Создаем назначения инструментальных исследований
    #     for _ in range(8):
    #         patient = random.choice(patients)
    #         name=random.choice(instrumental_procedures)
    #         doctor = random.choice(users)
    #         encounter = random.choice(encounters) if encounters else None
    #         
    #         assignment = InstrumentalProcedureAssignment.objects.create(
    #             content_type=encounter_content_type if encounter else None,
    #             object_id=encounter.id if encounter else None,
    #             patient=patient,
    #             assigning_doctor=doctor,
    #             instrumental_procedure=procedure,
    #             start_date=timezone.now() - timedelta(days=random.randint(1, 10)),
    #             status=random.choice(['active', 'completed'])
    #         )
    #         
    #         # Создаем результаты для некоторых назначений
    #         if random.choice([True, False]):
    #             InstrumentalProcedureResult.objects.create(
    #                 instrumental_procedure_assignment=assignment,
    #                 procedure_definition=procedure,
    #                 author=doctor,
    #                 datetime_result=timezone.now() - timedelta(days=random.randint(1, 5)),
    #                 data={
    #                         'conclusion': 'Патологии не выявлено',
    #                         'recommendations': 'Повторить через 6 месяцев',
    #                         'images_count': random.randint(1, 5)
    #                     }
    #                 )
    #     
    #     self.stdout.write('Созданы назначения лечения')

    def create_documents(self, patients, users, document_types, encounters):
        """Создает клинические документы"""
        encounter_content_type = ContentType.objects.get_for_model(Encounter)
        for _ in range(20):
            patient = random.choice(patients)
            user = random.choice(users)
            doc_type = random.choice(document_types)
            encounter = random.choice(encounters) if encounters else None
            
            # Создаем данные документа в зависимости от типа
            if 'История болезни' in doc_type.name:
                data = {
                    'complaints': 'Жалобы на головную боль, слабость',
                    'anamnesis': 'Заболел 3 дня назад',
                    'diagnosis': 'ОРВИ',
                    'treatment_plan': 'Симптоматическое лечение'
                }
            elif 'Выписной эпикриз' in doc_type.name:
                data = {
                    'admission_diagnosis': 'ОРВИ',
                    'discharge_diagnosis': 'ОРВИ, выздоровление',
                    'treatment_performed': 'Симптоматическое лечение',
                    'recommendations': 'Избегать переохлаждения'
                }
            else:
                data = {
                    'operation_name': 'Аппендэктомия',
                    'surgeon': 'Петров П.П.',
                    'anesthesia_type': 'Общая',
                    'operation_description': 'Проведена аппендэктомия'
                }
            
            ClinicalDocument.objects.create(
                document_type=doc_type,
                content_type=encounter_content_type if encounter else None,
                object_id=encounter.id if encounter else None,
                author=user,
                author_position='Врач',
                datetime_document=timezone.now() - timedelta(days=random.randint(1, 30)),
                data=data,
                is_signed=random.choice([True, False])
            )
        
        self.stdout.write('Созданы клинические документы') 