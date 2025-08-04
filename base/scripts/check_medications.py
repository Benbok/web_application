# scripts/check_medications.py
import os
import django
import sys

# Настройка окружения Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from pharmacy.models import Medication, Regimen, DosingInstruction, PopulationCriteria

def check_medications():
    print("=== Проверка данных о лекарствах в БД ===\n")
    
    # Общая статистика
    print(f"Всего препаратов: {Medication.objects.count()}")
    print(f"Всего схем применения: {Regimen.objects.count()}")
    print(f"Всего инструкций по дозированию: {DosingInstruction.objects.count()}")
    print(f"Всего критериев пациентов: {PopulationCriteria.objects.count()}")
    
    # Проверяем Цефтриаксон
    print("\n=== Детальная проверка Цефтриаксона ===")
    try:
        ceftriaxone = Medication.objects.get(name='Цефтриаксон')
        print(f"Препарат: {ceftriaxone.name}")
        print(f"Внешняя ссылка: {ceftriaxone.external_info_url}")
        print(f"Количество схем: {ceftriaxone.regimens.count()}")
        
        for reg in ceftriaxone.regimens.all():
            print(f"\n  Схема: {reg.name}")
            print(f"    Примечания: {reg.notes}")
            print(f"    Показания: {reg.indications.count()} диагнозов")
            print(f"    Критерии пациентов: {reg.population_criteria.count()}")
            print(f"    Инструкции по дозированию: {reg.dosing_instructions.count()}")
            
            for di in reg.dosing_instructions.all():
                print(f"      * Доза: {di.dose_description}")
                print(f"        Частота: {di.frequency_description}")
                print(f"        Длительность: {di.duration_description}")
                print(f"        Способ: {di.route.name if di.route else 'Не указан'}")
                print(f"        Тип: {di.get_dose_type_display()}")
            
            for pc in reg.population_criteria.all():
                print(f"      Критерии: {pc.name}")
                if pc.min_age_days:
                    print(f"        Мин. возраст: {pc.min_age_days} дней")
                if pc.max_age_days:
                    print(f"        Макс. возраст: {pc.max_age_days} дней")
                if pc.min_weight_kg:
                    print(f"        Мин. вес: {pc.min_weight_kg} кг")
                if pc.max_weight_kg:
                    print(f"        Макс. вес: {pc.max_weight_kg} кг")
                    
    except Medication.DoesNotExist:
        print("❌ Цефтриаксон не найден в БД")
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")

if __name__ == "__main__":
    check_medications() 