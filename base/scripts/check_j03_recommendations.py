#!/usr/bin/env python
"""
Скрипт для проверки рекомендаций по J03
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

from pharmacy.models import Medication, Regimen, Diagnosis
from pharmacy.services import PatientRecommendationService
from patients.models import Patient
from diagnosis.models import Diagnosis as DiagnosisModel

def check_j03_recommendations():
    """Проверяет рекомендации по J03"""
    print("=== ПРОВЕРКА РЕКОМЕНДАЦИЙ ПО J03 ===")
    
    # Проверяем диагноз J03
    print("\n1. Диагноз J03:")
    j03_diagnosis = DiagnosisModel.objects.filter(code='J03').first()
    if j03_diagnosis:
        print(f"   Найден: {j03_diagnosis.code} - {j03_diagnosis.name}")
    else:
        print("   Диагноз J03 не найден")
        return
    
    # Проверяем схемы с показанием J03
    print("\n2. Схемы с показанием J03:")
    j03_pharmacy = Diagnosis.objects.filter(code='J03').first()
    if j03_pharmacy:
        regimens_with_j03 = Regimen.objects.filter(indications=j03_pharmacy)
        print(f"   Найдено схем с показанием J03: {regimens_with_j03.count()}")
        for reg in regimens_with_j03:
            print(f"   - {reg.name} ({reg.medication.name})")
    else:
        print("   Диагноз J03 не найден в pharmacy")
    
    # Проверяем все схемы для Ампициллина
    print("\n3. Все схемы для Ампициллина:")
    ampicillin = Medication.objects.filter(name__icontains='Ампициллин').first()
    if ampicillin:
        print(f"   Найден: {ampicillin.name}")
        regimens = Regimen.objects.filter(medication=ampicillin)
        print(f"   Всего схем: {regimens.count()}")
        for reg in regimens:
            print(f"   - {reg.name}")
            if hasattr(reg, 'indications'):
                indications = reg.indications.all()
                print(f"     Показания: {indications.count()}")
                for ind in indications:
                    print(f"     - {ind.code}: {ind.name}")
    else:
        print("   Ампициллин не найден")
    
    # Тестируем сервис рекомендаций
    print("\n4. Тестирование сервиса рекомендаций:")
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
    
    print(f"   Рекомендации получены: {bool(recommendations)}")
    if 'error' in recommendations:
        print(f"   Ошибка: {recommendations['error']}")
    else:
        print(f"   Количество рекомендаций: {len(recommendations.get('recommendations', []))}")
        for i, rec in enumerate(recommendations.get('recommendations', []), 1):
            medication = rec.get('medication', {})
            regimen = rec.get('regimen', {})
            print(f"   {i}. {medication.get('name', 'Неизвестно')} - {regimen.get('dosage', 'Нет дозировки')}")

if __name__ == '__main__':
    check_j03_recommendations() 