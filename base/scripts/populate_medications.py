# scripts/populate_medications.py
import os
import django
import yaml
from decimal import Decimal

# Настройка окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings') # <-- ЗАМЕНИТЕ НА ВАШ ПРОЕКТ
django.setup()

from pharmacy.models import (
    MedicationGroup, ReleaseForm, AdministrationMethod, Medication,
    TradeName, Regimen, PopulationCriteria, DosingInstruction, RegimenAdjustment
)
from diagnosis.models import Diagnosis

# Путь к файлу с данными
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'medications.yaml')

def clear_database():
    """Очищает таблицы перед заполнением."""
    print("Clearing old data...")
    RegimenAdjustment.objects.all().delete()
    DosingInstruction.objects.all().delete()
    PopulationCriteria.objects.all().delete()
    Regimen.objects.all().delete()
    TradeName.objects.all().delete()
    Medication.objects.all().delete()
    MedicationGroup.objects.all().delete()
    ReleaseForm.objects.all().delete()
    AdministrationMethod.objects.all().delete()
    # Diagnosis.objects.all().delete()  # Не очищаем диагнозы - они статичные данные

def pre_populate_lookups(data):
    """
    Находит все уникальные значения для справочников в файле данных
    и создает их в базе, чтобы избежать ошибок при связывании.
    """
    print("Pre-populating lookup models (groups, forms, routes)...")
    groups = set()
    forms = set()
    routes = set()

    for med_data in data:
        if 'trade_names' in med_data:
            for tn in med_data['trade_names']:
                if 'group' in tn: groups.add(tn['group'])
                if 'release_form' in tn: forms.add(tn['release_form'])
        
        if 'regimens' in med_data:
            for reg_data in med_data['regimens']:
                if 'dosing_instructions' in reg_data:
                    for instr in reg_data['dosing_instructions']:
                        if 'route' in instr: routes.add(instr['route'])
    
    for group in groups: MedicationGroup.objects.get_or_create(name=group)
    for form in forms: ReleaseForm.objects.get_or_create(name=form)
    for route in routes: AdministrationMethod.objects.get_or_create(name=route)


def run():
    clear_database()

    print(f"Loading data from {DATA_FILE}...")
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            medications_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Data file not found at {DATA_FILE}. Please create it.")
        return
    
    pre_populate_lookups(medications_data)

    for med_data in medications_data:
        print(f"\nProcessing Medication: {med_data['medication_name']}")

        # Используем update_or_create для создания/обновления препарата вместе со ссылкой
        medication_obj, created = Medication.objects.update_or_create(
            name=med_data['medication_name'],
            defaults={
                'external_info_url': med_data.get('external_info_url', '') # .get() для безопасности
            }
        )
        
        # 1. Создаем препарат (МНН)
        medication_obj, _ = Medication.objects.get_or_create(name=med_data['medication_name'])

        # 2. Создаем торговые наименования
        for tn_data in med_data.get('trade_names', []):
            # Безопасно получаем или создаем связанные объекты, чтобы избежать ошибок
            group_obj, _ = MedicationGroup.objects.get_or_create(name=tn_data.get('group', 'Не указана'))
            form_obj, _ = ReleaseForm.objects.get_or_create(name=tn_data.get('release_form', 'Не указана'))

            TradeName.objects.update_or_create(
                medication=medication_obj,
                name=tn_data.get('name'),
                defaults={
                    'medication_group': group_obj,
                    'release_form': form_obj,
                    'atc_code': tn_data.get('atc_code', '') # <-- ДОБАВЛЕНО ПОЛЕ ATC
                }
            )

        # 3. Создаем схемы применения
        for reg_data in med_data.get('regimens', []):
            regimen_obj = Regimen.objects.create(
                medication=medication_obj,
                name=reg_data['name'],
                notes=reg_data.get('notes', '')
            )
            
            # Привязываем диагнозы (используем только существующие)
            if 'indications' in reg_data:
                diagnoses_qs = Diagnosis.objects.filter(code__in=reg_data['indications'])
                if diagnoses_qs.exists():
                    regimen_obj.indications.set(diagnoses_qs)
                else:
                    print(f"  ⚠️  Предупреждение: Диагнозы {reg_data['indications']} не найдены в базе данных")

            # Создаем критерии пациента
            for crit_data in reg_data.get('population_criteria', []):
                PopulationCriteria.objects.create(
                    regimen=regimen_obj,
                    name=crit_data['name'],
                    min_age_days=int(crit_data.get('min_age_years', 0) * 365),
                    max_age_days=int(crit_data.get('max_age_years', 0) * 365) if 'max_age_years' in crit_data else None,
                    min_weight_kg=Decimal(str(crit_data.get('min_weight_kg', 0.0))),
                )
            
            # Создаем инструкции по дозированию
            for instr_data in reg_data.get('dosing_instructions', []):
                route_obj = None
                if instr_data.get('route'):
                    route_obj, _ = AdministrationMethod.objects.get_or_create(name=instr_data.get('route'))

                DosingInstruction.objects.create(
                    regimen=regimen_obj,
                    dose_type=instr_data.get('type', 'MAINTENANCE'),
                    # Используем .get() с пустым значением по умолчанию, чтобы избежать ошибки
                    dose_description=instr_data.get('dose', ''),
                    frequency_description=instr_data.get('frequency', ''),
                    duration_description=instr_data.get('duration', ''),
                    route=route_obj
                )
            
            # Создаем корректировки
            for adj_data in reg_data.get('adjustments', []):
                RegimenAdjustment.objects.create(
                    regimen=regimen_obj,
                    condition=adj_data['condition'],
                    adjustment_description=adj_data['adjustment']
                )

    print("\nDatabase population from data file finished successfully! ✅")