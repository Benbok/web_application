#!/usr/bin/env python
"""
Скрипт для автоматического обновления модуля Documents
"""
import os
import sys
import django
import subprocess
import json
from pathlib import Path

# Добавляем путь к проекту
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.core.cache import cache


def run_command(command, description):
    """Выполнение команды с выводом"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} выполнено успешно")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Ошибка при {description.lower()}:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Исключение при {description.lower()}: {e}")
        return False
    return True


def backup_database():
    """Создание резервной копии базы данных"""
    backup_file = f"backup_documents_{django.utils.timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    command = f"python manage.py dumpdata documents > {backup_file}"
    
    if run_command(command, "Создание резервной копии базы данных"):
        print(f"📁 Резервная копия сохранена в: {backup_file}")
        return backup_file
    return None


def install_dependencies():
    """Установка зависимостей"""
    dependencies = [
        "django-redis",
        "reportlab",  # для PDF экспорта
        "python-docx",  # для DOCX экспорта
    ]
    
    for dep in dependencies:
        command = f"pip install {dep}"
        if not run_command(command, f"Установка {dep}"):
            return False
    return True


def run_migrations():
    """Выполнение миграций"""
    commands = [
        ("python manage.py makemigrations documents", "Создание миграций"),
        ("python manage.py migrate documents", "Выполнение миграций"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True


def update_existing_data():
    """Обновление существующих данных"""
    print("\n🔄 Обновление существующих данных...")
    
    try:
        from documents.models import ClinicalDocument, DocumentType, DocumentTemplate
        from documents.optimizations import DocumentSearch
        
        # Обновление статусов документов
        updated_docs = ClinicalDocument.objects.filter(is_archived__isnull=True).update(is_archived=False)
        print(f"✅ Обновлено {updated_docs} документов (is_archived)")
        
        updated_types = DocumentType.objects.filter(is_active__isnull=True).update(is_active=True)
        print(f"✅ Обновлено {updated_types} типов документов (is_active)")
        
        updated_templates = DocumentTemplate.objects.filter(is_active__isnull=True).update(is_active=True)
        print(f"✅ Обновлено {updated_templates} шаблонов (is_active)")
        
        # Обновление поисковых векторов (только для PostgreSQL)
        if 'postgresql' in connection.vendor:
            print("🔄 Обновление поисковых векторов для PostgreSQL...")
            count = 0
            for document in ClinicalDocument.objects.all():
                document.data_search = DocumentSearch.create_search_vector(document)
                document.save(update_fields=['data_search'])
                count += 1
            print(f"✅ Обновлено {count} поисковых векторов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении данных: {e}")
        return False


def test_cache():
    """Тестирование кэша"""
    print("\n🔄 Тестирование кэша...")
    
    try:
        # Тестируем кэш
        test_key = "test_cache_key"
        test_value = "test_value"
        
        cache.set(test_key, test_value, 60)
        retrieved_value = cache.get(test_key)
        
        if retrieved_value == test_value:
            print("✅ Кэш работает корректно")
            cache.delete(test_key)
            return True
        else:
            print("❌ Кэш не работает корректно")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании кэша: {e}")
        return False


def create_indexes():
    """Создание индексов для PostgreSQL"""
    print("\n🔄 Создание индексов для PostgreSQL...")
    
    if 'postgresql' not in connection.vendor:
        print("ℹ️ База данных не PostgreSQL, пропускаем создание индексов")
        return True
    
    indexes = [
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS document_data_gin_idx 
        ON documents_clinicaldocument USING GIN (data);
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS document_search_gin_idx 
        ON documents_clinicaldocument USING GIN (data_search);
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS document_type_date_idx 
        ON documents_clinicaldocument (document_type_id, datetime_document);
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS document_author_idx 
        ON documents_clinicaldocument (author_id);
        """,
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS document_status_idx 
        ON documents_clinicaldocument (is_signed, is_canceled, is_archived);
        """
    ]
    
    try:
        with connection.cursor() as cursor:
            for i, index_sql in enumerate(indexes, 1):
                print(f"🔄 Создание индекса {i}/{len(indexes)}...")
                cursor.execute(index_sql)
                print(f"✅ Индекс {i} создан")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании индексов: {e}")
        return False


def check_redis():
    """Проверка подключения к Redis"""
    print("\n🔄 Проверка подключения к Redis...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=1)
        r.ping()
        print("✅ Redis доступен")
        return True
    except Exception as e:
        print(f"❌ Redis недоступен: {e}")
        print("💡 Установите и запустите Redis:")
        print("   Ubuntu/Debian: sudo apt-get install redis-server")
        print("   macOS: brew install redis")
        print("   Windows: скачайте с https://redis.io/download")
        return False


def main():
    """Основная функция обновления"""
    print("🚀 Начало обновления модуля Documents")
    print("=" * 50)
    
    # Проверка текущей директории
    if not os.path.exists('manage.py'):
        print("❌ Скрипт должен быть запущен из корневой директории проекта")
        return False
    
    # Создание резервной копии
    backup_file = backup_database()
    if not backup_file:
        print("❌ Не удалось создать резервную копию")
        return False
    
    # Установка зависимостей
    if not install_dependencies():
        print("❌ Не удалось установить зависимости")
        return False
    
    # Проверка Redis
    if not check_redis():
        print("⚠️ Redis недоступен, кэширование будет отключено")
    
    # Выполнение миграций
    if not run_migrations():
        print("❌ Не удалось выполнить миграции")
        return False
    
    # Обновление данных
    if not update_existing_data():
        print("❌ Не удалось обновить данные")
        return False
    
    # Создание индексов
    if not create_indexes():
        print("⚠️ Не удалось создать индексы")
    
    # Тестирование кэша
    if not test_cache():
        print("⚠️ Кэш не работает")
    
    print("\n" + "=" * 50)
    print("✅ Обновление модуля Documents завершено успешно!")
    print(f"📁 Резервная копия: {backup_file}")
    print("\n📋 Следующие шаги:")
    print("1. Обновите импорты в views.py")
    print("2. Обновите URL-ы в главном urls.py")
    print("3. Настройте кэш в settings.py")
    print("4. Протестируйте функциональность")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 