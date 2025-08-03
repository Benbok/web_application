#!/usr/bin/env python
"""
Скрипт для отладки критериев возраста
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

from pharmacy.models import PopulationCriteria, Regimen, Diagnosis
from pharmacy.services import PatientRecommendationService
from patients.models import Patient
from diagnosis.models import Diagnosis as DiagnosisModel

def debug_age_criteria():
    """Отладка критериев возраста"""
    print("=== ОТЛАДКА КРИТЕРИЕВ ВОЗРАСТА ===")
    
    # Создаем пациентов разного возраста
    patients = []
    
    # Взрослый пациент (35 лет)
    adult_patient, created = Patient.objects.get_or_create(
        first_name='Взрослый',
        last_name='Пациент',
        defaults={'birth_date': '1990-01-01'}
    )
    patients.append(('Взрослый (35 лет)', adult_patient))
    
    # Молодой пациент (25 лет)
    young_patient, created = Patient.objects.get_or_create(
        first_name='Молодой',
        last_name='Пациент',
        defaults={'birth_date': '2000-01-01'}
    )
    patients.append(('Молодой (25 лет)', young_patient))
    
    # Ребенок (10 лет)
    child_patient, created = Patient.objects.get_or_create(
        first_name='Ребенок',
        last_name='Пациент',
        defaults={'birth_date': '2015-01-01'}
    )
    patients.append(('Ребенок (10 лет)', child_patient))
    
    # Получаем диагноз J03
    diagnosis = DiagnosisModel.objects.filter(code='J03').first()
    if not diagnosis:
        print("❌ Диагноз J03 не найден")
        return
    
    print(f"✅ Диагноз: {diagnosis.code} - {diagnosis.name}")
    
    # Проверяем критерии населения
    print("\n=== КРИТЕРИИ НАСЕЛЕНИЯ ===")
    criteria = PopulationCriteria.objects.all()
    for crit in criteria:
        print(f"  - {crit.name}")
        print(f"    Возраст: {crit.min_age_days or 0} - {crit.max_age_days or '∞'} дней")
        print(f"    Вес: {crit.min_weight_kg or 0} - {crit.max_weight_kg or '∞'} кг")
    
    # Тестируем каждого пациента
    for patient_name, patient in patients:
        age_days = (date.today() - patient.birth_date).days if patient.birth_date else 0
        print(f"\n=== ТЕСТИРОВАНИЕ {patient_name} ===")
        print(f"Возраст: {age_days} дней ({age_days/365.25:.1f} лет)")
        
        recommendations = PatientRecommendationService.get_patient_recommendations(
            patient=patient,
            diagnosis=diagnosis
        )
        
        print(f"Рекомендации: {len(recommendations)} препаратов")
        for med_name, regimens in recommendations.items():
            print(f"  - {med_name}: {len(regimens)} схем")
            for regimen in regimens:
                print(f"    * {regimen.get('regimen_name', 'Неизвестно')}")
                if regimen.get('suitable_criteria'):
                    for crit in regimen['suitable_criteria']:
                        print(f"      Критерии: {crit['name']}")

if __name__ == '__main__':
    from datetime import date
    debug_age_criteria() 