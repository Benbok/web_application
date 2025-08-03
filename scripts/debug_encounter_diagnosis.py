#!/usr/bin/env python
import os
import sys
import django

# Добавляем путь к проекту Django
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'base'))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from encounters.models import Encounter, EncounterDiagnosis
from encounters.forms import EncounterDiagnosisAdvancedForm
from diagnosis.models import Diagnosis

def test_encounter_diagnosis_creation():
    """Тестируем создание EncounterDiagnosis"""
    print("=== ТЕСТ СОЗДАНИЯ ENCOUNTER DIAGNOSIS ===")
    
    # Получаем первый случай обращения
    try:
        encounter = Encounter.objects.first()
        if not encounter:
            print("❌ Нет случаев обращения в базе данных")
            return
        
        print(f"✅ Найден случай обращения: {encounter}")
        print(f"   ID: {encounter.pk}")
        print(f"   Пациент: {encounter.patient}")
        
        # Получаем первый диагноз из справочника
        diagnosis = Diagnosis.objects.first()
        if not diagnosis:
            print("❌ Нет диагнозов в справочнике")
            return
        
        print(f"✅ Найден диагноз: {diagnosis}")
        
        # Создаем данные для формы
        form_data = {
            'diagnosis_type': 'main',
            'diagnosis': diagnosis.pk,
            'custom_diagnosis': '',
            'description': 'Тестовый диагноз'
        }
        
        print(f"📝 Данные формы: {form_data}")
        
        # Создаем форму
        form = EncounterDiagnosisAdvancedForm(data=form_data)
        
        if form.is_valid():
            print("✅ Форма валидна")
            
            # Создаем объект EncounterDiagnosis
            encounter_diagnosis = form.save(commit=False)
            encounter_diagnosis.encounter = encounter
            encounter_diagnosis.save()
            
            print(f"✅ EncounterDiagnosis создан: {encounter_diagnosis}")
            print(f"   Encounter: {encounter_diagnosis.encounter}")
            print(f"   Diagnosis: {encounter_diagnosis.diagnosis}")
            print(f"   Type: {encounter_diagnosis.diagnosis_type}")
            
        else:
            print("❌ Форма невалидна:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def test_encounter_diagnosis_without_encounter():
    """Тестируем создание EncounterDiagnosis без encounter"""
    print("\n=== ТЕСТ СОЗДАНИЯ БЕЗ ENCOUNTER ===")
    
    try:
        # Получаем первый диагноз из справочника
        diagnosis = Diagnosis.objects.first()
        if not diagnosis:
            print("❌ Нет диагнозов в справочнике")
            return
        
        # Создаем данные для формы
        form_data = {
            'diagnosis_type': 'main',
            'diagnosis': diagnosis.pk,
            'custom_diagnosis': '',
            'description': 'Тестовый диагноз'
        }
        
        # Создаем форму
        form = EncounterDiagnosisAdvancedForm(data=form_data)
        
        if form.is_valid():
            print("✅ Форма валидна")
            
            # Пытаемся создать объект без encounter
            encounter_diagnosis = form.save(commit=False)
            # НЕ устанавливаем encounter
            encounter_diagnosis.save()
            
            print(f"✅ EncounterDiagnosis создан: {encounter_diagnosis}")
            print(f"   Encounter: {encounter_diagnosis.encounter}")
            
        else:
            print("❌ Форма невалидна:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_encounter_diagnosis_creation()
    test_encounter_diagnosis_without_encounter() 