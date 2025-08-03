#!/usr/bin/env python
"""
Скрипт для проверки данных pharmacy
"""

import os
import sys
import django

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from pharmacy.models import Medication, TradeName, Regimen, Diagnosis
from diagnosis.models import Diagnosis as DiagnosisModel

def check_pharmacy_data():
    """Проверяет данные в pharmacy"""
    print("=== ПРОВЕРКА ДАННЫХ PHARMACY ===")
    
    # Проверяем лекарства
    print("\n1. Лекарства в базе данных:")
    medications = Medication.objects.all()
    print(f"   Всего лекарств: {medications.count()}")
    for med in medications[:5]:  # Показываем первые 5
        print(f"   - {med.name}")
    
    # Проверяем торговые названия
    print("\n2. Торговые названия:")
    trade_names = TradeName.objects.all()
    print(f"   Всего торговых названий: {trade_names.count()}")
    for tn in trade_names[:5]:
        print(f"   - {tn.name} ({tn.medication.name})")
    
    # Проверяем схемы применения
    print("\n3. Схемы применения:")
    regimens = Regimen.objects.all()
    print(f"   Всего схем: {regimens.count()}")
    for reg in regimens[:5]:
        print(f"   - {reg.name} ({reg.medication.name})")
    
    # Проверяем диагнозы
    print("\n4. Диагнозы в pharmacy:")
    pharmacy_diagnoses = Diagnosis.objects.all()
    print(f"   Всего диагнозов в pharmacy: {pharmacy_diagnoses.count()}")
    for diag in pharmacy_diagnoses[:5]:
        print(f"   - {diag.code}: {diag.name}")
    
    # Проверяем диагнозы в diagnosis app
    print("\n5. Диагнозы в diagnosis app:")
    diagnosis_diagnoses = DiagnosisModel.objects.all()
    print(f"   Всего диагнозов в diagnosis: {diagnosis_diagnoses.count()}")
    j03_diagnoses = diagnosis_diagnoses.filter(code__startswith='J03')
    print(f"   Диагнозы J03: {j03_diagnoses.count()}")
    for diag in j03_diagnoses:
        print(f"   - {diag.code}: {diag.name}")
    
    # Проверяем связи между схемами и диагнозами
    print("\n6. Связи схем с диагнозами:")
    for reg in regimens[:3]:
        print(f"   Схема '{reg.name}' для '{reg.medication.name}':")
        if hasattr(reg, 'indications'):
            indications = reg.indications.all()
            print(f"     Показания: {indications.count()}")
            for ind in indications:
                print(f"     - {ind.code}: {ind.name}")
        else:
            print("     Нет показаний")

if __name__ == '__main__':
    check_pharmacy_data() 