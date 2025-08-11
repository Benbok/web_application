# pharmacy/management/commands/load_med_data.py
import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pharmacy.models import (
    MedicationGroup, ReleaseForm, AdministrationMethod, Medication,
    TradeName, Regimen, PopulationCriteria, DosingInstruction,
    RegimenAdjustment
)
from diagnosis.models import Diagnosis

class Command(BaseCommand):
    
    help = 'Загружает данные о препаратах из YAML файла в базу данных'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Путь к YAML файлу с данными')

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options['file_path']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise CommandError(f"Файл не найден: {file_path}")
        except yaml.YAMLError as e:
            raise CommandError(f"Ошибка парсинга YAML файла: {e}")

        self.stdout.write("Начало импорта... Все операции выполняются в одной транзакции.")

        # Шаг 1: Загрузка справочников
        for group_data in data.get('medication_groups') or []:
            group, created = MedicationGroup.get_or_create_smart(
                group_data['name'], 
                group_data.get('description')
            )
            if created:
                self.stdout.write(f"Создана новая группа препаратов: {group.name}")
        
        for form_data in data.get('release_forms') or []:
            form, created = ReleaseForm.get_or_create_smart(
                form_data['name'], 
                form_data.get('description')
            )
            if created:
                self.stdout.write(f"Создана новая форма выпуска: {form.name}")
            
        for method_data in data.get('administration_methods') or []:
            method, created = AdministrationMethod.get_or_create_smart(
                method_data['name'], 
                method_data.get('description')
            )
            if created:
                self.stdout.write(f"Создан новый способ введения: {method.name}")

        self.stdout.write(self.style.SUCCESS("Справочники успешно загружены."))

        # Шаг 2: Загрузка МНН (убираем несуществующие поля)
        for med_data in data.get('medications') or []:
            # Убираем поле atc_code, которого нет в модели Medication
            # Но оставляем external_info_url и другие допустимые поля
            allowed_fields = ['name', 'is_active', 'medication_form', 'external_info_url', 'code', 'generic_concept', 'trade_name']
            med_data_clean = {k: v for k, v in med_data.items() if k in allowed_fields}
            
            # Создаем или обновляем запись
            medication, created = Medication.objects.get_or_create(
                name=med_data_clean['name'], 
                defaults=med_data_clean
            )
            
            # Если запись уже существовала, обновляем её
            if not created:
                for field, value in med_data_clean.items():
                    if field != 'name':  # Не обновляем имя, так как оно используется как ключ
                        setattr(medication, field, value)
                medication.save()
        
        self.stdout.write(self.style.SUCCESS("МНН (Medications) успешно загружены."))

        # Шаг 3: Загрузка торговых наименований
        for tn_data in data.get('trade_names') or []:
            # Создаем копию данных для безопасного изменения
            tn_data_copy = tn_data.copy()
            
            # Находим связанные объекты, используя умные методы
            medication = Medication.objects.get(name=tn_data_copy.pop('medication_name'))
            group, _ = MedicationGroup.get_or_create_smart(tn_data_copy.pop('group_name'))
            release_form, _ = ReleaseForm.get_or_create_smart(tn_data_copy.pop('release_form_name'))
            
            # Убираем поле atc_code, если оно есть в данных
            if 'atc_code' in tn_data_copy:
                atc_code = tn_data_copy.pop('atc_code')
            else:
                atc_code = None
            
            # Создаем объект TradeName с корректными defaults
            trade_name, created = TradeName.objects.get_or_create(
                name=tn_data_copy['name'],
                medication=medication,
                defaults={
                    'medication_group': group,
                    'release_form': release_form,
                    'atc_code': atc_code,
                    **tn_data_copy  # Теперь сюда попадут external_info_url и другие поля
                }
            )
            
            # Если запись уже существовала, обновляем её
            if not created:
                trade_name.medication_group = group
                trade_name.release_form = release_form
                trade_name.atc_code = atc_code
                # Обновляем другие поля
                for field, value in tn_data_copy.items():
                    if field not in ['name', 'medication_name', 'group_name', 'release_form_name']:
                        setattr(trade_name, field, value)
                trade_name.save()

        self.stdout.write(self.style.SUCCESS("Торговые наименования (TradeNames) успешно загружены."))

        # Шаг 4: Загрузка схем применения
        for regimen_data in data.get('regimens') or []:
            medication = Medication.objects.get(name=regimen_data['medication_name'])
            
            # Извлекаем вложенные данные
            criteria_list = regimen_data.pop('population_criteria', [])
            instructions_list = regimen_data.pop('dosing_instructions', [])
            adjustments_list = regimen_data.pop('adjustments', [])
            indication_codes = regimen_data.pop('indications', [])
            
            # Убираем служебные поля из defaults
            regimen_data_clean = {k: v for k, v in regimen_data.items() if k in ['name', 'notes']}
            
            # Создаем или получаем схему
            regimen, created = Regimen.objects.get_or_create(
                medication=medication,
                name=regimen_data_clean['name'],
                defaults=regimen_data_clean
            )
            
            # Привязываем диагнозы (M2M)
            indications = Diagnosis.objects.filter(code__in=indication_codes)
            regimen.indications.set(indications)
            
            # Создаем вложенные объекты
            for criteria_data in criteria_list:
                PopulationCriteria.objects.get_or_create(regimen=regimen, **criteria_data)
                
            for instruction_data in instructions_list:
                route_name = instruction_data.pop('route')
                # Используем умный метод для автоматического создания способа введения
                route, created = AdministrationMethod.get_or_create_smart(route_name)
                if created:
                    self.stdout.write(f"Создан новый способ введения: {route_name}")
                DosingInstruction.objects.get_or_create(regimen=regimen, route=route, **instruction_data)
                
            for adjustment_data in adjustments_list:
                RegimenAdjustment.objects.get_or_create(regimen=regimen, **adjustment_data)

        self.stdout.write(self.style.SUCCESS("Схемы применения (Regimens) успешно загружены."))
        self.stdout.write(self.style.SUCCESS("Импорт успешно завершен."))

# python manage.py load_med_data pharmacy/management/commands/data/pharmacy_data.yaml