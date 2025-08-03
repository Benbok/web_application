#!/usr/bin/env python
"""
Отладка несоответствия диагнозов
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

from pharmacy.models import Diagnosis as PharmacyDiagnosis
from diagnosis.models import Diagnosis as DiagnosisModel

def debug_diagnosis_mismatch():
    """Отладка несоответствия диагнозов"""
    print("=== ОТЛАДКА НЕСООТВЕТСТВИЯ ДИАГНОЗОВ ===")
    
    # Получаем диагнозы J03
    diagnosis_j03 = DiagnosisModel.objects.filter(code='J03.9').first()
    pharmacy_j03 = PharmacyDiagnosis.objects.filter(code='J03').first()
    
    print(f"Диагноз в diagnosis app:")
    if diagnosis_j03:
        print(f"  - {diagnosis_j03.code}: {diagnosis_j03.name}")
        print(f"  - ID: {diagnosis_j03.id}")
    else:
        print("  ❌ Не найден")
    
    print(f"\nДиагноз в pharmacy app:")
    if pharmacy_j03:
        print(f"  - {pharmacy_j03.code}: {pharmacy_j03.name}")
        print(f"  - ID: {pharmacy_j03.id}")
    else:
        print("  ❌ Не найден")
    
    # Проверяем все диагнозы J03
    print(f"\nВсе диагнозы J03 в diagnosis app:")
    diagnosis_j03_all = DiagnosisModel.objects.filter(code__startswith='J03')
    for diag in diagnosis_j03_all:
        print(f"  - {diag.code}: {diag.name}")
    
    print(f"\nВсе диагнозы J03 в pharmacy app:")
    pharmacy_j03_all = PharmacyDiagnosis.objects.filter(code__startswith='J03')
    for diag in pharmacy_j03_all:
        print(f"  - {diag.code}: {diag.name}")
    
    # Проверяем связи схем
    from pharmacy.models import Regimen
    
    print(f"\nСхемы для диагноза из diagnosis app:")
    if diagnosis_j03:
        regimens_diagnosis = Regimen.objects.filter(indications=diagnosis_j03)
        print(f"  Найдено: {regimens_diagnosis.count()}")
        for reg in regimens_diagnosis:
            print(f"    - {reg.name} ({reg.medication.name})")
    
    print(f"\nСхемы для диагноза из pharmacy app:")
    if pharmacy_j03:
        regimens_pharmacy = Regimen.objects.filter(indications=pharmacy_j03)
        print(f"  Найдено: {regimens_pharmacy.count()}")
        for reg in regimens_pharmacy:
            print(f"    - {reg.name} ({reg.medication.name})")

if __name__ == '__main__':
    debug_diagnosis_mismatch() 