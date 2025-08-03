#!/usr/bin/env python
"""
Проверка J03.9 в pharmacy
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

from pharmacy.models import Diagnosis as PharmacyDiagnosis, Regimen
from pharmacy.services import PatientRecommendationService
from patients.models import Patient
from datetime import date

def check_j03_9_pharmacy():
    """Проверка J03.9 в pharmacy"""
    print("=== ПРОВЕРКА J03.9 В PHARMACY ===")
    
    # Создаем пациента
    patient, created = Patient.objects.get_or_create(
        first_name='Тест',
        last_name='Пациент',
        defaults={'birth_date': date(1990, 1, 1)}
    )
    
    # Получаем диагноз J03.9 в pharmacy
    pharmacy_diagnosis = PharmacyDiagnosis.objects.filter(code='J03.9').first()
    if not pharmacy_diagnosis:
        print("❌ Диагноз J03.9 не найден в pharmacy")
        return
    
    print(f"✅ Диагноз: {pharmacy_diagnosis.code} - {pharmacy_diagnosis.name}")
    
    # Получаем схемы для этого диагноза
    regimens = Regimen.objects.filter(indications=pharmacy_diagnosis)
    print(f"✅ Схем для J03.9: {regimens.count()}")
    
    for reg in regimens:
        print(f"  - {reg.name} ({reg.medication.name})")
    
    # Тестируем рекомендации
    recommendations = PatientRecommendationService.get_patient_recommendations(
        patient=patient,
        diagnosis=pharmacy_diagnosis
    )
    
    print(f"\nРекомендации: {bool(recommendations)}")
    print(f"Количество препаратов: {len(recommendations)}")
    
    for med_name, regimens in recommendations.items():
        print(f"\nПрепарат: {med_name}")
        print(f"Количество схем: {len(regimens)}")
        for regimen in regimens:
            print(f"  - {regimen.get('regimen_name', 'Неизвестно')}")

if __name__ == '__main__':
    check_j03_9_pharmacy() 