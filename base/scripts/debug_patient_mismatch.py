#!/usr/bin/env python
"""
Скрипт для отладки несоответствия пациентов
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

from encounters.services import TreatmentPlanService
from encounters.models import Encounter
from patients.models import Patient
from diagnosis.models import Diagnosis
from django.contrib.auth.models import User
from pharmacy.services import PatientRecommendationService

def debug_patient_mismatch():
    """Отладка несоответствия пациентов"""
    print("=== ОТЛАДКА НЕСООТВЕТСТВИЯ ПАЦИЕНТОВ ===")
    
    # Создаем тестовые данные
    user, created = User.objects.get_or_create(
        username='test_doctor_debug',
        defaults={'email': 'test@example.com', 'first_name': 'Тест', 'last_name': 'Врач'}
    )
    
    patient, created = Patient.objects.get_or_create(
        first_name='Тест',
        last_name='Пациент',
        defaults={'birth_date': '1990-01-01'}
    )
    
    diagnosis, created = Diagnosis.objects.get_or_create(
        code='J03.9',
        defaults={'name': 'Острый тонзиллит неуточненный'}
    )
    
    # Создаем случай обращения
    encounter = Encounter.objects.create(
        patient=patient,
        doctor=user,
        diagnosis=None
    )
    
    # Добавляем основной диагноз
    main_diag = encounter.add_diagnosis(
        diagnosis_type='main',
        diagnosis=diagnosis,
        description='Основное заболевание'
    )
    
    print(f"✅ Создан случай: {encounter.pk}")
    print(f"✅ Пациент: {encounter.patient.full_name}")
    print(f"✅ Возраст пациента: {(date.today() - encounter.patient.birth_date).days} дней")
    print(f"✅ Диагноз: {main_diag}")
    
    # Тестируем напрямую с тем же пациентом
    print("\n=== ПРЯМОЕ ТЕСТИРОВАНИЕ С ПАЦИЕНТОМ ENCOUNTER ===")
    
    direct_recommendations = PatientRecommendationService.get_patient_recommendations(
        patient=encounter.patient,
        diagnosis=diagnosis
    )
    
    print(f"Прямые рекомендации получены: {bool(direct_recommendations)}")
    print(f"Количество препаратов: {len(direct_recommendations)}")
    
    # Тестируем через TreatmentPlanService
    print("\n=== ТЕСТИРОВАНИЕ ЧЕРЕЗ TREATMENTPLANSERVICE ===")
    
    service_recommendations = TreatmentPlanService.get_medication_recommendations(encounter)
    
    print(f"Рекомендации через сервис: {bool(service_recommendations)}")
    if 'recommendations' in service_recommendations:
        print(f"Количество рекомендаций: {len(service_recommendations['recommendations'])}")
    
    # Сравниваем пациентов
    print("\n=== СРАВНЕНИЕ ПАЦИЕНТОВ ===")
    print(f"Пациент encounter: {encounter.patient.id} - {encounter.patient.full_name}")
    print(f"Пациент прямой: {patient.id} - {patient.full_name}")
    print(f"Одинаковые пациенты: {encounter.patient.id == patient.id}")
    
    # Очистка
    encounter.delete()
    print("\n✅ Тестовые данные удалены")

if __name__ == '__main__':
    from datetime import date
    debug_patient_mismatch() 