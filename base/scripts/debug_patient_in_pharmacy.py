#!/usr/bin/env python
"""
Отладка пациента в pharmacy
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

from pharmacy.models import Regimen, Diagnosis as PharmacyDiagnosis, PopulationCriteria
from patients.models import Patient
from diagnosis.models import Diagnosis
from datetime import date

def debug_patient_in_pharmacy():
    """Отладка пациента в pharmacy"""
    print("=== ОТЛАДКА ПАЦИЕНТА В PHARMACY ===")
    
    # Создаем пациента
    patient, created = Patient.objects.get_or_create(
        first_name='Тест',
        last_name='Пациент',
        defaults={'birth_date': date(1990, 1, 1)}
    )
    
    # Создаем диагноз
    diagnosis, created = Diagnosis.objects.get_or_create(
        code='J03.9',
        defaults={'name': 'Острый тонзиллит неуточненный'}
    )
    
    print(f"✅ Пациент: {patient.full_name}")
    print(f"✅ Возраст: {(date.today() - patient.birth_date).days} дней")
    print(f"✅ Диагноз: {diagnosis.code} - {diagnosis.name}")
    
    # Получаем диагноз в pharmacy
    pharmacy_diagnosis = PharmacyDiagnosis.objects.filter(code='J03').first()
    if not pharmacy_diagnosis:
        print("❌ Диагноз J03 не найден в pharmacy")
        return
    
    print(f"✅ Диагноз в pharmacy: {pharmacy_diagnosis.code} - {pharmacy_diagnosis.name}")
    
    # Получаем схемы для этого диагноза
    regimens = Regimen.objects.filter(indications=pharmacy_diagnosis)
    print(f"✅ Найдено схем для J03: {regimens.count()}")
    
    age_days = (date.today() - patient.birth_date).days
    
    for reg in regimens:
        print(f"\nСхема: {reg.name} ({reg.medication.name})")
        criteria_count = reg.population_criteria.count()
        print(f"  Критериев населения: {criteria_count}")
        
        # Проверяем каждый критерий
        for criteria in reg.population_criteria.all():
            print(f"    Критерий: {criteria.name}")
            print(f"      Возраст: {criteria.min_age_days or 0} - {criteria.max_age_days or '∞'} дней")
            print(f"      Вес: {criteria.min_weight_kg or 0} - {criteria.max_weight_kg or '∞'} кг")
            
            # Проверяем подходит ли пациент
            from pharmacy.services import PatientRecommendationService
            is_suitable = PatientRecommendationService._is_patient_suitable(criteria, age_days, None)
            print(f"      Подходит: {is_suitable}")
            
            if is_suitable:
                print(f"      ✅ ПАЦИЕНТ ПОДХОДИТ!")
            else:
                print(f"      ❌ ПАЦИЕНТ НЕ ПОДХОДИТ")

if __name__ == '__main__':
    debug_patient_in_pharmacy() 