from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from examination_management.models import ExaminationPlan, ExaminationInstrumental
from examination_management.services import ExaminationIntegrationService
from instrumental_procedures.models import InstrumentalProcedureDefinition, InstrumentalProcedureResult
from clinical_scheduling.models import ScheduledAppointment
from patients.models import Patient
from encounters.models import Encounter, Department

User = get_user_model()


class Command(BaseCommand):
    help = 'Диагностирует проблему с автоматической установкой статуса "выполнено"'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Начинаем диагностику проблемы...'))
        
        try:
            with transaction.atomic():
                # Создаем тестовые данные
                user = self.create_test_user()
                department = self.create_test_department()
                patient = self.create_test_patient()
                encounter = self.create_test_encounter(patient, department, user)
                examination_plan = self.create_test_examination_plan(encounter, user)
                procedure_def = self.create_test_procedure_definition()
                
                self.stdout.write('Тестовые данные созданы.')
                
                # Проверяем начальное состояние
                self.stdout.write('\n=== СОЗДАНИЕ ExaminationInstrumental ===')
                
                # Создаем ExaminationInstrumental
                examination = ExaminationInstrumental.objects.create(
                    examination_plan=examination_plan,
                    instrumental_procedure=procedure_def,
                    priority='normal',
                    notes='Тестовое исследование'
                )
                
                self.stdout.write(f'ExaminationInstrumental создан: ID={examination.id}, статус={examination.status}')
                
                # Проверяем, что создалось в других приложениях
                results = InstrumentalProcedureResult.objects.filter(
                    examination_plan=examination_plan,
                    procedure_definition=procedure_def
                )
                self.stdout.write(f'Найдено InstrumentalProcedureResult: {results.count()}')
                
                if results.exists():
                    result = results.first()
                    self.stdout.write(f'Результат: ID={result.id}, is_completed={result.is_completed}')
                    
                    # Проверяем подписи
                    from document_signatures.models import DocumentSignature
                    signatures = DocumentSignature.objects.filter(
                        content_type__model='instrumentalprocedureresult',
                        object_id=result.id
                    )
                    self.stdout.write(f'Найдено подписей: {signatures.count()}')
                    
                    for sig in signatures:
                        self.stdout.write(f'  Подпись: тип={sig.signature_type}, статус={sig.status}')
                
                # Проверяем запланированные события
                appointments = ScheduledAppointment.objects.filter(
                    content_type__model='examinationinstrumental',
                    object_id=examination.id
                )
                self.stdout.write(f'Найдено ScheduledAppointment: {appointments.count()}')
                
                for apt in appointments:
                    self.stdout.write(f'  Событие: статус={apt.execution_status}, дата={apt.scheduled_date}')
                
                # Проверяем итоговый статус
                examination.refresh_from_db()
                self.stdout.write(f'\nИтоговый статус ExaminationInstrumental: {examination.status}')
                
                # Эмулируем заполнение данных
                self.stdout.write('\n=== ЗАПОЛНЕНИЕ ДАННЫХ ===')
                if results.exists():
                    result = results.first()
                    result.data_fields = {"test": "data"}
                    result.is_completed = True
                    result.save()
                    self.stdout.write(f'Данные заполнены, is_completed={result.is_completed}')
                    
                    # Проверяем изменения статуса
                    examination.refresh_from_db()
                    self.stdout.write(f'Статус ExaminationInstrumental после заполнения: {examination.status}')
                
                # Откатываем транзакцию, чтобы не замусорить БД
                raise Exception("Откат тестовой транзакции")
                
        except Exception as e:
            if "Откат тестовой транзакции" in str(e):
                self.stdout.write(self.style.SUCCESS('\nТест завершен, изменения откатаны.'))
            else:
                self.stdout.write(self.style.ERROR(f'Ошибка во время теста: {e}'))
                raise

    def create_test_user(self):
        user, created = User.objects.get_or_create(
            username='test_debug_user',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        return user

    def create_test_department(self):
        department, created = Department.objects.get_or_create(
            name='Test Department',
            defaults={'slug': 'test-debug-dept'}
        )
        return department

    def create_test_patient(self):
        patient, created = Patient.objects.get_or_create(
            first_name='Test',
            last_name='Patient',
            defaults={
                'birth_date': timezone.now().date(),
                'gender': Patient.Gender.MALE
            }
        )
        return patient

    def create_test_encounter(self, patient, department, user):
        encounter, created = Encounter.objects.get_or_create(
            patient=patient,
            date_start=timezone.now(),
            defaults={
                'doctor': user,
                'is_active': True
            }
        )
        return encounter

    def create_test_examination_plan(self, encounter, user):
        plan, created = ExaminationPlan.objects.get_or_create(
            encounter=encounter,
            defaults={
                'created_by': user,
                'name': 'Test Plan',
                'description': 'Test examination plan'
            }
        )
        return plan

    def create_test_procedure_definition(self):
        procedure, created = InstrumentalProcedureDefinition.objects.get_or_create(
            name='Test Procedure',
            defaults={
                'description': 'Тестовая процедура для отладки',
                'schema': {"fields": [{"name": "test", "type": "text"}]}
            }
        )
        return procedure