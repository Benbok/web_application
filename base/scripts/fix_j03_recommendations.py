#!/usr/bin/env python
"""
Скрипт для исправления рекомендаций по J03
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

from pharmacy.models import Regimen, PopulationCriteria, Diagnosis
from pharmacy.services import PatientRecommendationService
from patients.models import Patient
from diagnosis.models import Diagnosis as DiagnosisModel

def fix_j03_recommendations():
    """Исправляет рекомендации по J03"""
    print("=== ИСПРАВЛЕНИЕ РЕКОМЕНДАЦИЙ ПО J03 ===")
    
    # Получаем диагноз J03
    j03_diagnosis = DiagnosisModel.objects.filter(code='J03').first()
    if not j03_diagnosis:
        print("❌ Диагноз J03 не найден")
        return
    
    print(f"✅ Найден диагноз: {j03_diagnosis.code} - {j03_diagnosis.name}")
    
    # Получаем схемы для J03
    j03_regimens = Regimen.objects.filter(indications__code='J03')
    print(f"✅ Найдено схем для J03: {j03_regimens.count()}")
    
    # Получаем критерии населения
    adult_criteria = PopulationCriteria.objects.filter(name__icontains='Взрослые').first()
    child_criteria = PopulationCriteria.objects.filter(name__icontains='Дети').first()
    
    if not adult_criteria:
        print("❌ Критерии для взрослых не найдены")
        return
    
    if not child_criteria:
        print("❌ Критерии для детей не найдены")
        return
    
    print(f"✅ Найдены критерии: {adult_criteria.name}, {child_criteria.name}")
    
    # Проверяем и добавляем критерии к схемам
    fixed_count = 0
    for regimen in j03_regimens:
        current_criteria = regimen.population_criteria.count()
        print(f"\nСхема: {regimen.name} ({regimen.medication.name})")
        print(f"  Текущих критериев: {current_criteria}")
        
        if current_criteria == 0:
            # Определяем подходящий критерий по названию схемы
            if 'взрослых' in regimen.name.lower():
                regimen.population_criteria.add(adult_criteria)
                print(f"  ✅ Добавлен критерий: {adult_criteria.name}")
                fixed_count += 1
            elif 'детей' in regimen.name.lower():
                regimen.population_criteria.add(child_criteria)
                print(f"  ✅ Добавлен критерий: {child_criteria.name}")
                fixed_count += 1
            else:
                # По умолчанию добавляем критерий для взрослых
                regimen.population_criteria.add(adult_criteria)
                print(f"  ✅ Добавлен критерий по умолчанию: {adult_criteria.name}")
                fixed_count += 1
        else:
            print(f"  ✅ Критерии уже есть")
    
    print(f"\n✅ Исправлено схем: {fixed_count}")
    
    # Тестируем рекомендации
    print("\n=== ТЕСТИРОВАНИЕ РЕКОМЕНДАЦИЙ ===")
    
    # Создаем тестового пациента
    patient, created = Patient.objects.get_or_create(
        first_name='Тест',
        last_name='Пациент',
        defaults={'birth_date': '1990-01-01'}
    )
    
    recommendations = PatientRecommendationService.get_patient_recommendations(
        patient=patient,
        diagnosis=j03_diagnosis
    )
    
    print(f"Рекомендации получены: {bool(recommendations)}")
    if recommendations:
        print(f"Количество рекомендаций: {len(recommendations)}")
        for medication_name, recs in recommendations.items():
            print(f"\nПрепарат: {medication_name}")
            for i, rec in enumerate(recs, 1):
                print(f"  {i}. {rec['regimen_name']}")
                if rec['suitable_criteria']:
                    for crit in rec['suitable_criteria']:
                        print(f"     Критерии: {crit['name']}")
                if rec['dosing_instructions']:
                    for dose in rec['dosing_instructions']:
                        print(f"     Дозировка: {dose['dose_description']} - {dose['frequency']}")
    else:
        print("❌ Рекомендации не найдены")

if __name__ == '__main__':
    fix_j03_recommendations() 