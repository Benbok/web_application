#!/usr/bin/env python
"""
Скрипт для детальной отладки рекомендаций
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

def debug_recommendations():
    """Детальная отладка рекомендаций"""
    print("=== ДЕТАЛЬНАЯ ОТЛАДКА РЕКОМЕНДАЦИЙ ===")
    
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
    print(f"✅ Добавлен диагноз: {main_diag}")
    
    # Тестируем получение рекомендаций
    print("\n=== ТЕСТИРОВАНИЕ РЕКОМЕНДАЦИЙ ===")
    
    recommendations = TreatmentPlanService.get_medication_recommendations(encounter)
    print(f"Рекомендации получены: {bool(recommendations)}")
    print(f"Тип рекомендаций: {type(recommendations)}")
    print(f"Ключи: {list(recommendations.keys()) if isinstance(recommendations, dict) else 'Не словарь'}")
    
    if 'error' in recommendations:
        print(f"❌ Ошибка: {recommendations['error']}")
    elif 'recommendations' in recommendations:
        recs = recommendations['recommendations']
        print(f"✅ Количество рекомендаций: {len(recs)}")
        for i, rec in enumerate(recs, 1):
            print(f"\nРекомендация {i}:")
            print(f"  Лекарство: {rec.get('medication', {}).get('name', 'Неизвестно')}")
            print(f"  Схема: {rec.get('regimen', {}).get('name', 'Неизвестно')}")
            print(f"  Дозировка: {rec.get('regimen', {}).get('dosage', 'Неизвестно')}")
            print(f"  Частота: {rec.get('regimen', {}).get('frequency', 'Неизвестно')}")
    else:
        print(f"❌ Неожиданный формат: {recommendations}")
    
    # Тестируем создание плана лечения
    print("\n=== ТЕСТИРОВАНИЕ СОЗДАНИЯ ПЛАНА ===")
    
    treatment_plan = TreatmentPlanService.create_treatment_plan_with_recommendations(
        encounter=encounter,
        name='Тестовый план лечения',
        description='План создан для тестирования'
    )
    
    print(f"✅ План лечения создан: {treatment_plan.name}")
    print(f"✅ Количество лекарств: {treatment_plan.medications.count()}")
    
    for med in treatment_plan.medications.all():
        print(f"  - {med.medication.name if med.medication else med.custom_medication}")
        print(f"    Дозировка: {med.dosage}")
        print(f"    Частота: {med.frequency}")
    
    # Очистка
    encounter.delete()
    print("\n✅ Тестовые данные удалены")

if __name__ == '__main__':
    debug_recommendations() 