import os
import django
import pandas as pd

# Настройка окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings') # <-- ЗАМЕНИТЕ НА ВАШ ПРОЕКТ
django.setup()

from diagnosis.models import Diagnosis

# Путь к файлу с данными МКБ-10 в формате XLSX
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'mkb10.xlsx')

def clear_database():
    """Очищает таблицу Diagnosis перед заполнением."""
    print("Очистка старых данных диагнозов...")
    Diagnosis.objects.all().delete()

def run():
    """Основная функция для запуска скрипта."""
    clear_database()
    
    diagnoses_to_create = []
    
    print(f"Чтение данных из Excel файла {DATA_FILE}...")
    try:
        # ----- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ ЗДЕСЬ -----
        df = pd.read_excel(
            DATA_FILE,
            header=None,       # Не ищем строку с заголовками
            skiprows=4,        # Пропускаем первые 4 строки (начинаем с 5-й)
            usecols="A:B",     # Используем только колонки A и B
            names=['code', 'name'] # Принудительно называем их 'code' и 'name'
        )
        # ------------------------------------

        # Заменяем пустые ячейки (NaN) на пустые строки для безопасности
        df = df.fillna('')

        # Проходим по каждой строке DataFrame
        for row in df.itertuples(index=False):
            code = str(row.code).strip()
            name = str(row.name).strip()

            # Пропускаем строки без кода или названия, а также диапазоны
            if not code or not name or '-' in code:
                continue

            diagnoses_to_create.append(
                Diagnosis(code=code, name=name)
            )
                
    except FileNotFoundError:
        print(f"ОШИБКА: Файл с данными не найден по пути {DATA_FILE}.")
        return
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
        return

    # Массово создаем объекты в базе данных
    if diagnoses_to_create:
        print(f"Найдено {len(diagnoses_to_create)} диагнозов. Загрузка в базу данных...")
        Diagnosis.objects.bulk_create(diagnoses_to_create, ignore_conflicts=True)
    
    print("\nЗагрузка данных МКБ-10 из XLSX файла успешно завершена! ✅")