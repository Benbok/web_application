#!/usr/bin/env python
"""
Скрипт для проверки критериев населения
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

from pharmacy.models import Regimen, PopulationCriteria
from diagnosis.models import Diagnosis

def check_population_criteria():
    """Проверяет критерии населения"""
    print("=== ПРОВЕРКА КРИТЕРИЕВ НАСЕЛЕНИЯ ===")
    
    # Проверяем все критерии населения
    print("\n1. Все критерии населения:")
    criteria = PopulationCriteria.objects.all()
    print(f"   Всего критериев: {criteria.count()}")
    for crit in criteria[:5]:
        print(f"   - {crit.name} (возраст: {crit.min_age_days or 0}-{crit.max_age_days or '∞'}, вес: {crit.min_weight_kg or 0}-{crit.max_weight_kg or '∞'})")
    
    # Проверяем схемы с критериями населения
    print("\n2. Схемы с критериями населения:")
    regimens_with_criteria = Regimen.objects.filter(population_criteria__isnull=False).distinct()
    print(f"   Схем с критериями: {regimens_with_criteria.count()}")
    
    # Проверяем схемы для J03
    print("\n3. Схемы для J03:")
    j03_diagnosis = Diagnosis.objects.filter(code='J03').first()
    if j03_diagnosis:
        j03_regimens = Regimen.objects.filter(indications=j03_diagnosis)
        print(f"   Всего схем для J03: {j03_regimens.count()}")
        for reg in j03_regimens:
            criteria_count = reg.population_criteria.count()
            print(f"   - {reg.name} ({reg.medication.name}) - критериев: {criteria_count}")
            if criteria_count == 0:
                print(f"     ⚠️  НЕТ КРИТЕРИЕВ НАСЕЛЕНИЯ")
    
    # Проверяем схемы для Ампициллина
    print("\n4. Схемы для Ампициллина:")
    ampicillin_regimens = Regimen.objects.filter(medication__name__icontains='Ампициллин')
    print(f"   Всего схем для Ампициллина: {ampicillin_regimens.count()}")
    for reg in ampicillin_regimens:
        criteria_count = reg.population_criteria.count()
        print(f"   - {reg.name} - критериев: {criteria_count}")
        if criteria_count == 0:
            print(f"     ⚠️  НЕТ КРИТЕРИЕВ НАСЕЛЕНИЯ")

if __name__ == '__main__':
    check_population_criteria() 