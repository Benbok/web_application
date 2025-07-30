#!/usr/bin/env python
"""
Скрипт для исправления дублирования способов введения в базе данных.
Объединяет дублирующиеся записи и обновляет связанные данные.
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from pharmacy.models import AdministrationMethod, DosingInstruction
from django.db import transaction

def fix_administration_methods():
    """
    Исправляет дублирование способов введения.
    """
    print("🔧 Начинаем исправление дублирования способов введения...")
    
    # Словарь для маппинга дублирующихся названий
    method_mapping = {
        # Основные способы введения
        "Внутривенно (инфузия)": "Внутривенно",
        "Внутривенно, Внутримышечно": "Внутривенно или Внутримышечно",
        "Внутримышечно или Внутривенно": "Внутривенно или Внутримышечно",
        "Внутривенно или Внутримышечно": "Внутривенно или Внутримышечно",
        
        # Дополнительные варианты
        "Внутривенно или Перорально": "Внутривенно или Перорально",
        "Перорально (внутрь)": "Перорально",
        "Местно (в конъюнктивальный мешок)": "Местно",
        "Наружно": "Наружно",
    }
    
    with transaction.atomic():
        # Получаем все способы введения
        all_methods = AdministrationMethod.objects.all()
        print(f"📊 Найдено {all_methods.count()} способов введения в базе данных")
        
        # Создаем словарь существующих методов
        existing_methods = {}
        for method in all_methods:
            existing_methods[method.name] = method
        
        # Создаем новые методы, если их нет
        new_methods_created = 0
        for old_name, new_name in method_mapping.items():
            if new_name not in existing_methods:
                method = AdministrationMethod.objects.create(
                    name=new_name,
                    description=f"Стандартизированный способ введения: {new_name}"
                )
                existing_methods[new_name] = method
                new_methods_created += 1
                print(f"✅ Создан новый способ введения: '{new_name}'")
        
        # Обновляем инструкции по дозированию
        updated_instructions = 0
        for instruction in DosingInstruction.objects.all():
            if instruction.route and instruction.route.name in method_mapping:
                old_name = instruction.route.name
                new_name = method_mapping[old_name]
                new_method = existing_methods[new_name]
                
                instruction.route = new_method
                instruction.save()
                updated_instructions += 1
                print(f"🔄 Обновлена инструкция: '{old_name}' → '{new_name}'")
        
        # Удаляем дублирующиеся методы
        deleted_methods = 0
        for old_name in method_mapping.keys():
            if old_name in existing_methods:
                method = existing_methods[old_name]
                # Проверяем, что нет связанных инструкций
                if not DosingInstruction.objects.filter(route=method).exists():
                    method.delete()
                    deleted_methods += 1
                    print(f"🗑️ Удален дублирующийся способ: '{old_name}'")
                else:
                    print(f"⚠️ Не удалось удалить '{old_name}' - есть связанные инструкции")
        
        # Выводим статистику
        print("\n📈 СТАТИСТИКА ИСПРАВЛЕНИЙ:")
        print(f"   • Создано новых методов: {new_methods_created}")
        print(f"   • Обновлено инструкций: {updated_instructions}")
        print(f"   • Удалено дублирующихся методов: {deleted_methods}")
        
        # Показываем финальный список методов
        final_methods = AdministrationMethod.objects.all().order_by('name')
        print(f"\n📋 ФИНАЛЬНЫЙ СПИСОК СПОСОБОВ ВВЕДЕНИЯ ({final_methods.count()}):")
        for method in final_methods:
            instruction_count = DosingInstruction.objects.filter(route=method).count()
            print(f"   • {method.name} ({instruction_count} инструкций)")
        
        print("\n✅ Исправление дублирования завершено!")

def show_current_methods():
    """
    Показывает текущие способы введения и их использование.
    """
    print("📊 ТЕКУЩИЕ СПОСОБЫ ВВЕДЕНИЯ:")
    
    methods = AdministrationMethod.objects.all().order_by('name')
    for method in methods:
        instruction_count = DosingInstruction.objects.filter(route=method).count()
        print(f"   • {method.name} ({instruction_count} инструкций)")
    
    print(f"\nВсего способов введения: {methods.count()}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_current_methods()
    else:
        fix_administration_methods() 
        
# python manage.py fix_administration_methods --show-only - показать текущие способы введения
# python manage.py fix_administration_methods --dry-run - предварительный просмотр изменений
# python manage.py fix_administration_methods - выполнить исправление