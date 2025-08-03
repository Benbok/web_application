#!/usr/bin/env python
"""
Скрипт для отладки pharmacy сервиса
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

from pharmacy.services import PatientRecommendationService
from patients.models import Patient
from diagnosis.models import Diagnosis

def debug_pharmacy_service():
    """Отладка pharmacy сервиса"""
    print("=== ОТЛАДКА PHARMACY СЕРВИСА ===")
    
    # Создаем тестового пациента
    patient, created = Patient.objects.get_or_create(
        first_name='Тест',
        last_name='Пациент',
        defaults={'birth_date': '1990-01-01'}
    )
    
    # Получаем диагноз J03
    diagnosis = Diagnosis.objects.filter(code='J03').first()
    if not diagnosis:
        print("❌ Диагноз J03 не найден")
        return
    
    print(f"✅ Пациент: {patient.full_name} (возраст: {(date.today() - patient.birth_date).days} дней)")
    print(f"✅ Диагноз: {diagnosis.code} - {diagnosis.name}")
    
    # Тестируем сервис рекомендаций
    print("\n=== ТЕСТИРОВАНИЕ СЕРВИСА ===")
    
    recommendations = PatientRecommendationService.get_patient_recommendations(
        patient=patient,
        diagnosis=diagnosis
    )
    
    print(f"Рекомендации получены: {bool(recommendations)}")
    print(f"Тип: {type(recommendations)}")
    print(f"Ключи: {list(recommendations.keys()) if isinstance(recommendations, dict) else 'Не словарь'}")
    
    if recommendations:
        print(f"Количество препаратов: {len(recommendations)}")
        for medication_name, regimens in recommendations.items():
            print(f"\nПрепарат: {medication_name}")
            print(f"Количество схем: {len(regimens)}")
            for i, regimen in enumerate(regimens, 1):
                print(f"  {i}. {regimen.get('regimen_name', 'Неизвестно')}")
                if regimen.get('suitable_criteria'):
                    for crit in regimen['suitable_criteria']:
                        print(f"     Критерии: {crit['name']}")
                if regimen.get('dosing_instructions'):
                    for dose in regimen['dosing_instructions']:
                        print(f"     Дозировка: {dose.get('dose_description', 'Неизвестно')}")
    else:
        print("❌ Рекомендации не найдены")
    
    # Проверяем схемы напрямую
    print("\n=== ПРЯМАЯ ПРОВЕРКА СХЕМ ===")
    
    from pharmacy.models import Regimen, Diagnosis as PharmacyDiagnosis
    
    # Получаем диагноз в pharmacy
    pharmacy_diagnosis = PharmacyDiagnosis.objects.filter(code='J03').first()
    if pharmacy_diagnosis:
        regimens = Regimen.objects.filter(indications=pharmacy_diagnosis)
        print(f"Найдено схем для J03: {regimens.count()}")
        
        for reg in regimens:
            print(f"\nСхема: {reg.name} ({reg.medication.name})")
            criteria_count = reg.population_criteria.count()
            print(f"  Критериев населения: {criteria_count}")
            
            # Проверяем подходящие критерии
            age_in_days = (date.today() - patient.birth_date).days
            suitable_criteria = []
            for criteria in reg.population_criteria.all():
                if PatientRecommendationService._is_patient_suitable(criteria, age_in_days, None):
                    suitable_criteria.append(criteria)
            
            print(f"  Подходящих критериев: {len(suitable_criteria)}")
            for crit in suitable_criteria:
                print(f"    - {crit.name}")
    else:
        print("❌ Диагноз J03 не найден в pharmacy")

if __name__ == '__main__':
    from datetime import date
    debug_pharmacy_service() 