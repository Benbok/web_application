#!/usr/bin/env python
"""
Скрипт для запуска тестов сервисов pharmacy.
Запускает Django management command для тестирования.
"""

import os
import sys
import subprocess

def main():
    # Переходим в директорию base (на уровень выше scripts)
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    os.chdir(base_dir)
    
    print("Запуск тестов сервисов Pharmacy...")
    print("=" * 50)
    
    try:
        # Запускаем Django management command
        result = subprocess.run([
            sys.executable, 'manage.py', 'test_pharmacy_services'
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении тестов:")
        print(e.stdout)
        print(e.stderr)
        return 1
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return 1
    
    print("\n" + "=" * 50)
    print("Тесты завершены успешно!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 