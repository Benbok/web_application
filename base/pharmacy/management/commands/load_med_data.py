# pharmacy/management/commands/load_med_data.py
import os
import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pharmacy.models import (
    MedicationGroup, ReleaseForm, AdministrationMethod, Medication,
    TradeName, Regimen, PopulationCriteria, DosingInstruction,
    RegimenAdjustment
)
# Убедитесь, что модель Диагнозов импортируется правильно
from diagnosis.models import Diagnosis

class Command(BaseCommand):
    
    help = 'Загружает полные данные о препаратах из многодокументного YAML файла в базу данных.'

    def add_arguments(self, parser):
        parser.add_argument('yaml_file', type=str, help='Путь к YAML файлу с данными')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно удалить и пересоздать все связанные записи.'
        )

    def _parse_multi_document_yaml(self, file_path):
        """
        Парсит YAML файл с несколькими документами (разделенными '---')
        и объединяет данные из всех документов в единую структуру.
        """
        self.stdout.write("🔍 Начинаю парсинг многодокументного YAML файла...")
        
        # Структура для сбора данных из всех документов
        merged_data = {
            'medication_groups': [],
            'release_forms': [],
            'administration_methods': [],
            'medications': [],
            'trade_names': [],
            'regimens': []
        }
        
        processed_groups = set()
        processed_forms = set()
        processed_methods = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # yaml.safe_load_all читает все документы из файла, разделенные '---'
                self.stdout.write("   📖 Читаю YAML файл...")
                yaml_documents = yaml.safe_load_all(file)
                
                self.stdout.write(f"   📊 Тип yaml_documents: {type(yaml_documents)}")
                
                if yaml_documents is None:
                    self.stdout.write(self.style.WARNING("⚠️  YAML файл пуст или не содержит документов"))
                    return merged_data
                
                # Преобразуем в список для отладки
                yaml_documents = list(yaml_documents)
                self.stdout.write(f"   📊 Количество документов: {len(yaml_documents)}")
                
                for i, doc in enumerate(yaml_documents):
                    self.stdout.write(f"   📄 Документ {i+1}: {type(doc)}")
                    if not doc:
                        self.stdout.write(f"   ⚠️  Документ {i+1} пустой, пропускаю")
                        continue
                    
                    self.stdout.write(f"   🔍 Ключи в документе {i+1}: {list(doc.keys())}")
                    
                    # Собираем уникальные справочные данные
                    for group in doc.get('medication_groups', []) or []:
                        if group and isinstance(group, dict) and group.get('name'):
                            if group['name'] not in processed_groups:
                                merged_data['medication_groups'].append(group)
                                processed_groups.add(group['name'])
                    
                    for form in doc.get('release_forms', []) or []:
                        if form and isinstance(form, dict) and form.get('name'):
                            if form['name'] not in processed_forms:
                                merged_data['release_forms'].append(form)
                                processed_forms.add(form['name'])

                    for method in doc.get('administration_methods', []) or []:
                        if method and isinstance(method, dict) and method.get('name'):
                            if method['name'] not in processed_methods:
                                merged_data['administration_methods'].append(method)
                                processed_methods.add(method['name'])

                    # Добавляем основные данные
                    for key in ['medications', 'trade_names', 'regimens']:
                        try:
                            if key in doc and doc[key] and isinstance(doc[key], list):
                                self.stdout.write(f"   📝 Добавляю {len(doc[key])} записей из {key}")
                                # Фильтруем None значения
                                valid_items = [item for item in doc[key] if item is not None]
                                if len(valid_items) != len(doc[key]):
                                    self.stdout.write(f"   ⚠️  Отфильтровано {len(doc[key]) - len(valid_items)} None значений из {key}")
                                merged_data[key].extend(valid_items)
                            elif key in doc:
                                self.stdout.write(f"   ⚠️  Ключ {key} есть, но значение: {type(doc[key])} = {doc[key]}")
                        except Exception as e:
                            self.stdout.write(f"   ❌ Ошибка при обработке ключа {key}: {e}")
                            self.stdout.write(f"   📊 Значение ключа {key}: {doc.get(key)}")
                            continue

            self.stdout.write(f"📊 Итоговая статистика парсинга:")
            self.stdout.write(f"   МНН: {len(merged_data['medications'])}")
            self.stdout.write(f"   Торговые названия: {len(merged_data['trade_names'])}")
            self.stdout.write(f"   Схемы: {len(merged_data['regimens'])}")
            
            return merged_data
            
        except Exception as e:
            self.stdout.write(f"   ❌ Критическая ошибка при парсинге: {e}")
            import traceback
            self.stdout.write(f"   📊 Traceback: {traceback.format_exc()}")
            return merged_data

    @transaction.atomic
    def handle(self, *args, **options):
        yaml_file = options['yaml_file']
        force_mode = options.get('force', False)
        
        if not os.path.exists(yaml_file):
            raise CommandError(f'Файл {yaml_file} не найден!')

        self.stdout.write(f'📁 Загружаю данные из файла: {yaml_file}')
        
        if force_mode:
            self.stdout.write(self.style.WARNING("🔧 Режим --force: Удаление всех существующих данных..."))
            from pharmacy.models import (
                RegimenAdjustment, DosingInstruction, PopulationCriteria,
                Regimen, TradeName, Medication, MedicationGroup,
                ReleaseForm, AdministrationMethod
            )
            RegimenAdjustment.objects.all().delete()
            DosingInstruction.objects.all().delete()
            PopulationCriteria.objects.all().delete()
            Regimen.objects.all().delete()
            TradeName.objects.all().delete()
            Medication.objects.all().delete()
            MedicationGroup.objects.all().delete()
            ReleaseForm.objects.all().delete()
            AdministrationMethod.objects.all().delete()
            self.stdout.write("   ✅ Все связанные данные были удалены.")

        try:
            data = self._parse_multi_document_yaml(yaml_file)
            
            # === 1. ЗАГРУЗКА СПРАВОЧНИКОВ ===
            self.stdout.write("📋 Загружаю справочники...")
            for group_data in data.get('medication_groups', []):
                MedicationGroup.objects.update_or_create(name=group_data['name'], defaults=group_data)
            
            for form_data in data.get('release_forms', []):
                ReleaseForm.objects.update_or_create(name=form_data['name'], defaults=form_data)
            
            for method_data in data.get('administration_methods', []):
                AdministrationMethod.objects.update_or_create(name=method_data['name'], defaults=method_data)
            self.stdout.write("   ✅ Справочники загружены.")

                        # === 2. ЗАГРУЗКА МНН (Medications) ===
            self.stdout.write("📋 Загружаю МНН...")
            for med_data in data.get('medications', []):
                # Проверяем, есть ли atc_code, иначе используем пустую строку
                atc_code = med_data.get('atc_code')
                if atc_code is None:
                    atc_code = ''
                
                med_defaults = {
                    'is_active': med_data.get('is_active', True),
                    'medication_form': med_data.get('medication_form'),
                    'external_info_url': med_data.get('external_info_url'),
                    'code': atc_code
                }
                Medication.objects.update_or_create(name=med_data['name'], defaults=med_defaults)
            self.stdout.write("   ✅ МНН загружены.")
            
            # === 3. ЗАГРУЗКА ТОРГОВЫХ НАЗВАНИЙ (TradeNames) ===
            self.stdout.write("📋 Загружаю торговые названия...")
            for tn_data in data.get('trade_names', []):
                try:
                    medication = Medication.objects.get(name=tn_data['medication_name'])
                    group = MedicationGroup.objects.get(name=tn_data['group_name'])
                    release_form = ReleaseForm.objects.get(name=tn_data['release_form_name'])
                    
                    tn_defaults = {
                        'medication_group': group,
                        'release_form': release_form,
                        'atc_code': tn_data.get('atc_code'),
                        'external_info_url': tn_data.get('external_info_url')
                    }
                    TradeName.objects.update_or_create(
                        name=tn_data['name'],
                        medication=medication,
                        defaults=tn_defaults
                    )
                except (Medication.DoesNotExist, MedicationGroup.DoesNotExist, ReleaseForm.DoesNotExist) as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Пропуск '{tn_data['name']}': не найдена связанная запись. Ошибка: {e}"))
            self.stdout.write("   ✅ Торговые названия загружены.")
            
            # === 3.1. ЗАПОЛНЕНИЕ ПОЛЯ trade_name В МНН ===
            self.stdout.write("📋 Заполняю поле trade_name в МНН...")
            for medication in Medication.objects.all():
                # Получаем первое торговое название для этого МНН
                first_trade_name = TradeName.objects.filter(medication=medication).first()
                if first_trade_name:
                    medication.trade_name = first_trade_name.name
                    medication.save()
                    self.stdout.write(f"   ✅ {medication.name}: trade_name = {first_trade_name.name}")
                else:
                    self.stdout.write(f"   ⚠️  {medication.name}: нет торговых названий")
            self.stdout.write("   ✅ Поле trade_name заполнено.")
            
            # === 3.2. ОБНОВЛЕНИЕ МНН ДАННЫМИ ИЗ ТОРГОВЫХ НАЗВАНИЙ ===
            self.stdout.write("📋 Обновляю МНН данными из торговых названий...")
            for medication in Medication.objects.all():
                # Получаем первое торговое название для этого МНН
                first_trade_name = TradeName.objects.filter(medication=medication).first()
                if first_trade_name:
                    update_needed = False
                    
                    # Обновляем ATC код, если он пустой в МНН
                    if not medication.code and first_trade_name.atc_code:
                        medication.code = first_trade_name.atc_code
                        update_needed = True
                        self.stdout.write(f"   ✅ {medication.name}: добавлен ATC код {first_trade_name.atc_code}")
                    
                    # Обновляем внешнюю ссылку, если она пустая в МНН
                    if not medication.external_info_url and first_trade_name.external_info_url:
                        medication.external_info_url = first_trade_name.external_info_url
                        update_needed = True
                        self.stdout.write(f"   ✅ {medication.name}: добавлена внешняя ссылка")
                    
                    if update_needed:
                        medication.save()
                else:
                    self.stdout.write(f"   ⚠️  {medication.name}: нет торговых названий")
            self.stdout.write("   ✅ МНН обновлены данными из торговых названий.")

            # === 4. ЗАГРУЗКА СХЕМ ЛЕЧЕНИЯ (Regimens) ===
            self.stdout.write("📋 Загружаю схемы лечения...")
            for regimen_data in data.get('regimens', []):
                try:
                    medication = Medication.objects.get(name=regimen_data['medication_name'])
                    
                    # Создаем или обновляем основную схему
                    regimen, created = Regimen.objects.update_or_create(
                        medication=medication,
                        name=regimen_data['name'],
                        defaults={'notes': regimen_data.get('notes')}
                    )
                    
                    # Очищаем старые связанные данные для этого regimen, чтобы избежать дублей
                    regimen.population_criteria.all().delete()
                    regimen.dosing_instructions.all().delete()
                    regimen.adjustments.all().delete()

                    # Связываем с диагнозами (Many-to-Many)
                    indication_codes = regimen_data.get('indications', [])
                    if indication_codes:
                        diagnoses = Diagnosis.objects.filter(code__in=indication_codes)
                        regimen.indications.set(diagnoses)
                    
                    # Создаем вложенные PopulationCriteria
                    for pc_data in regimen_data.get('population_criteria', []):
                        # Фильтруем только существующие поля модели
                        from pharmacy.models import PopulationCriteria
                        valid_pc_fields = {k: v for k, v in pc_data.items() 
                                         if hasattr(PopulationCriteria, k)}
                        PopulationCriteria.objects.create(regimen=regimen, **valid_pc_fields)
                        
                    # Создаем вложенные DosingInstruction
                    for di_data in regimen_data.get('dosing_instructions', []):
                        # Связываем с методом по имени
                        if di_data.get('route'):
                            route_obj, _ = AdministrationMethod.objects.get_or_create(name=di_data['route'])
                            di_data['route'] = route_obj
                        # Фильтруем только существующие поля модели
                        from pharmacy.models import DosingInstruction
                        valid_di_fields = {k: v for k, v in di_data.items() 
                                         if hasattr(DosingInstruction, k)}
                        DosingInstruction.objects.create(regimen=regimen, **valid_di_fields)
                    
                    # Создаем вложенные RegimenAdjustment
                    for ra_data in regimen_data.get('adjustments', []):
                        # Фильтруем только существующие поля модели
                        from pharmacy.models import RegimenAdjustment
                        valid_ra_fields = {k: v for k, v in ra_data.items() 
                                         if hasattr(RegimenAdjustment, k)}
                        RegimenAdjustment.objects.create(regimen=regimen, **valid_ra_fields)

                except Medication.DoesNotExist as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Пропуск схемы '{regimen_data['name']}': не найден МНН. Ошибка: {e}"))
            self.stdout.write("   ✅ Схемы лечения загружены.")

            self.stdout.write(self.style.SUCCESS('✅✅✅ Все данные успешно загружены!'))

        except yaml.YAMLError as e:
            raise CommandError(f'❌ Ошибка парсинга YAML: {e}')
        except Exception as e:
            # Оборачиваем в CommandError, чтобы Django красиво показал ошибку
            raise CommandError(f'❌ Произошла критическая ошибка при загрузке данных: {e}')