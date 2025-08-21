#!/usr/bin/env python
"""
Пример использования мягкого удаления и синхронизации статусов

Этот скрипт демонстрирует, как работает система мягкого удаления
и автоматической синхронизации между приложениями.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from treatment_management.models import TreatmentMedication, TreatmentPlan
from examination_management.models import ExaminationLabTest, ExaminationPlan
from clinical_scheduling.models import ScheduledAppointment
from patients.models import Patient
from encounters.models import Encounter

User = get_user_model()


def create_test_data():
    """Создает тестовые данные для демонстрации"""
    print("🔧 Создание тестовых данных...")
    
    # Создаем тестового пользователя с уникальными данными
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    
    user, created = User.objects.get_or_create(
        username=f'test_doctor_{unique_suffix}',
        defaults={
            'first_name': 'Тест',
            'last_name': 'Врач',
            'email': f'test_{unique_suffix}@example.com'
        }
    )
    if created:
        print(f"✅ Создан пользователь: {user}")
    else:
        print(f"ℹ Используем существующего пользователя: {user}")
    
    # Создаем тестового пациента с уникальными данными
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    
    patient, created = Patient.objects.get_or_create(
        first_name=f'Тест_{unique_suffix}',
        last_name='Пациент',
        defaults={
            'middle_name': 'Тестович',
            'birth_date': '1990-01-01'
        }
    )
    if created:
        print(f"✅ Создан пациент: {patient}")
    else:
        print(f"ℹ Используем существующего пациента: {patient}")
    
    # Создаем случай обращения
    encounter, created = Encounter.objects.get_or_create(
        patient=patient,
        defaults={
            'date_start': timezone.now(),
            'doctor': user
        }
    )
    if created:
        print(f"✅ Создан случай обращения: {encounter}")
    else:
        print(f"ℹ Используем существующий случай обращения: {encounter}")
    
    # Создаем план лечения
    treatment_plan, created = TreatmentPlan.objects.get_or_create(
        encounter=encounter,
        name="Основной",
        defaults={
            'description': 'Основной план лечения для демонстрации',
            'created_by': user
        }
    )
    if created:
        print(f"✅ Создан план лечения: {treatment_plan}")
    
    # Создаем план обследования
    examination_plan, created = ExaminationPlan.objects.get_or_create(
        encounter=encounter,
        name="Основной",
        defaults={
            'description': 'Основной план обследования для демонстрации',
            'created_by': user
        }
    )
    if created:
        print(f"✅ Создан план обследования: {examination_plan}")
    
    return user, patient, encounter, treatment_plan, examination_plan


def demonstrate_treatment_medication_soft_delete(user, treatment_plan):
    """Демонстрирует мягкое удаление назначения лекарства"""
    print("\n💊 Демонстрация мягкого удаления назначения лекарства")
    print("=" * 60)
    
    # Создаем назначение лекарства
    medication = TreatmentMedication.objects.create(
        treatment_plan=treatment_plan,
        custom_medication="Аспирин",
        dosage="100 мг",
        frequency="2 раза в день",
        instructions="Принимать после еды"
    )
    print(f"✅ Создано назначение: {medication}")
    print(f"   Статус: {medication.get_status_display()}")
    
    # Создаем или получаем отделение
    from departments.models import Department
    department, created = Department.objects.get_or_create(
        name='Терапевтическое отделение',
        defaults={'description': 'Отделение для демонстрации'}
    )
    if created:
        print(f"✅ Создано отделение: {department}")
    
    # Создаем запланированное событие
    content_type = ContentType.objects.get_for_model(TreatmentMedication)
    appointment = ScheduledAppointment.objects.create(
        content_type=content_type,
        object_id=medication.pk,
        patient=medication.treatment_plan.encounter.patient,
        created_department=department,
        encounter=medication.treatment_plan.encounter,
        scheduled_date=timezone.now().date() + timedelta(days=1),
        scheduled_time=timezone.now().time(),
        execution_status='scheduled'
    )
    print(f"✅ Создано запланированное событие: {appointment}")
    print(f"   Статус выполнения: {appointment.get_execution_status_display()}")
    
    # Демонстрируем приостановку
    print(f"\n⏸️  Приостанавливаем назначение...")
    medication.pause(
        reason="Временная аллергическая реакция",
        paused_by=user
    )
    print(f"✅ Назначение приостановлено")
    print(f"   Статус: {medication.get_status_display()}")
    print(f"   Причина: {medication.pause_reason}")
    print(f"   Приостановил: {medication.paused_by}")
    print(f"   Дата приостановки: {medication.paused_at}")
    
    # Проверяем синхронизацию с расписанием
    appointment.refresh_from_db()
    print(f"   Статус события: {appointment.get_execution_status_display()}")
    
    # Демонстрируем возобновление
    print(f"\n▶️  Возобновляем назначение...")
    medication.resume()
    print(f"✅ Назначение возобновлено")
    print(f"   Статус: {medication.get_status_display()}")
    
    # Проверяем синхронизацию с расписанием
    appointment.refresh_from_db()
    print(f"   Статус события: {appointment.get_execution_status_display()}")
    
    # Демонстрируем отмену (мягкое удаление)
    print(f"\n❌ Отменяем назначение (мягкое удаление)...")
    medication.cancel(
        reason="Пациент отказался от лечения",
        cancelled_by=user
    )
    print(f"✅ Назначение отменено")
    print(f"   Статус: {medication.get_status_display()}")
    print(f"   Причина: {medication.cancellation_reason}")
    print(f"   Отменил: {medication.cancelled_by}")
    print(f"   Дата отмены: {medication.cancelled_at}")
    
    # Проверяем синхронизацию с расписанием
    appointment.refresh_from_db()
    print(f"   Статус события: {appointment.get_execution_status_display()}")
    
    # Показываем историю изменений
    print(f"\n📋 История изменений статуса:")
    history = medication.get_status_history()
    for change in history:
        if change['status'] == 'cancelled':
            print(f"   ❌ {change['status']}: {change['date']} - {change['reason']}")
        elif change['status'] == 'paused':
            print(f"   ⏸️  {change['status']}: {change['date']} - {change['reason']}")
    
    return medication


def demonstrate_examination_lab_test_soft_delete(user, examination_plan):
    """Демонстрирует мягкое удаление лабораторного исследования"""
    print("\n🧪 Демонстрация мягкого удаления лабораторного исследования")
    print("=" * 60)
    
    # Создаем лабораторное исследование
    from lab_tests.models import LabTestDefinition
    
    lab_test_def, created = LabTestDefinition.objects.get_or_create(
        name="Общий анализ крови",
        defaults={'description': 'Стандартный анализ крови'}
    )
    
    lab_test = ExaminationLabTest.objects.create(
        examination_plan=examination_plan,
        lab_test=lab_test_def,
        instructions="Сдавать натощак"
    )
    print(f"✅ Создано лабораторное исследование: {lab_test}")
    print(f"   Статус: {lab_test.get_status_display()}")
    
    # Создаем или получаем отделение
    from departments.models import Department
    department, created = Department.objects.get_or_create(
        name='Терапевтическое отделение',
        defaults={'description': 'Отделение для демонстрации'}
    )
    if created:
        print(f"✅ Создано отделение: {department}")
    
    # Создаем запланированное событие
    content_type = ContentType.objects.get_for_model(ExaminationLabTest)
    appointment = ScheduledAppointment.objects.create(
        content_type=content_type,
        object_id=lab_test.pk,
        patient=lab_test.examination_plan.encounter.patient,
        created_department=department,
        encounter=lab_test.examination_plan.encounter,
        scheduled_date=timezone.now().date() + timedelta(days=2),
        scheduled_time=timezone.now().time(),
        execution_status='scheduled'
    )
    print(f"✅ Создано запланированное событие: {appointment}")
    print(f"   Статус выполнения: {appointment.get_execution_status_display()}")
    
    # Демонстрируем отмену
    print(f"\n❌ Отменяем лабораторное исследование...")
    lab_test.cancel(
        reason="Пациент не явился на исследование",
        cancelled_by=user
    )
    print(f"✅ Исследование отменено")
    print(f"   Статус: {lab_test.get_status_display()}")
    print(f"   Причина: {lab_test.cancellation_reason}")
    
    # Проверяем синхронизацию с расписанием
    appointment.refresh_from_db()
    print(f"   Статус события: {appointment.get_execution_status_display()}")
    
    return lab_test


def demonstrate_status_queries():
    """Демонстрирует запросы по статусам"""
    print("\n🔍 Демонстрация запросов по статусам")
    print("=" * 60)
    
    # Подсчитываем назначения по статусам
    active_medications = TreatmentMedication.objects.filter(status='active').count()
    cancelled_medications = TreatmentMedication.objects.filter(status='cancelled').count()
    paused_medications = TreatmentMedication.objects.filter(status='paused').count()
    completed_medications = TreatmentMedication.objects.filter(status='completed').count()
    
    print(f"📊 Статистика назначений лекарств:")
    print(f"   Активные: {active_medications}")
    print(f"   Отмененные: {cancelled_medications}")
    print(f"   Приостановленные: {paused_medications}")
    print(f"   Завершенные: {completed_medications}")
    
    # Находим недавно отмененные назначения
    recent_cancelled = TreatmentMedication.objects.filter(
        status='cancelled',
        cancelled_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('cancelled_by', 'treatment_plan__encounter__patient')
    
    print(f"\n📅 Недавно отмененные назначения (за последние 7 дней):")
    for med in recent_cancelled:
        patient_name = med.treatment_plan.encounter.patient.full_name
        cancelled_by = med.cancelled_by.get_full_name() if med.cancelled_by else "Неизвестно"
        print(f"   💊 {med.get_medication_name()} - {patient_name}")
        print(f"      Отменил: {cancelled_by}")
        print(f"      Причина: {med.cancellation_reason}")
        print(f"      Дата: {med.cancelled_at.strftime('%d.%m.%Y %H:%M')}")


def main():
    """Основная функция демонстрации"""
    print("🚀 Демонстрация системы мягкого удаления и синхронизации статусов")
    print("=" * 80)
    
    try:
        # Создаем тестовые данные
        user, patient, encounter, treatment_plan, examination_plan = create_test_data()
        
        # Демонстрируем мягкое удаление назначения лекарства
        medication = demonstrate_treatment_medication_soft_delete(user, treatment_plan)
        
        # Демонстрируем мягкое удаление лабораторного исследования
        lab_test = demonstrate_examination_lab_test_soft_delete(user, examination_plan)
        
        # Демонстрируем запросы по статусам
        demonstrate_status_queries()
        
        print("\n🎉 Демонстрация завершена успешно!")
        print("\n📝 Что было продемонстрировано:")
        print("   ✅ Создание назначений и запланированных событий")
        print("   ✅ Приостановка назначений с указанием причины")
        print("   ✅ Возобновление приостановленных назначений")
        print("   ✅ Отмена назначений (мягкое удаление)")
        print("   ✅ Автоматическая синхронизация с расписанием")
        print("   ✅ Сохранение полной истории изменений")
        print("   ✅ Запросы по статусам назначений")
        
        print(f"\n💡 Попробуйте в админке Django:")
        print(f"   - Посмотреть назначение: {medication}")
        print(f"   - Посмотреть лабораторное исследование: {lab_test}")
        print(f"   - Проверить синхронизацию в clinical_scheduling")
        
    except Exception as e:
        print(f"❌ Ошибка при демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 