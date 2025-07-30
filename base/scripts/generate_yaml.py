import os
import django
import yaml
import re
from bs4 import BeautifulSoup

# Настройка окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings') # <-- ЗАМЕНИТЕ НА ВАШ ПРОЕКТ
django.setup()

# Определяем пути
BASE_DIR = os.path.dirname(__file__)
SOURCE_HTML_DIR = os.path.join(BASE_DIR, 'data', 'html_sources')
OUTPUT_YAML_FILE = os.path.join(BASE_DIR, 'data', 'medications.yaml')

def parse_html_file(file_path):
    """
    Анализирует один HTML-файл и извлекает структурированную информацию о препарате.
    (Улучшенная версия с защитой от ошибок)
    """
    print(f"  Анализ файла: {os.path.basename(file_path)}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        # --- Извлечение базовой информации с проверками ---
        h1_tag = soup.find('td', class_='h1')
        if not h1_tag:
            print(f"    ПРЕДУПРЕЖДЕНИЕ: Не найден основной заголовок h1 в файле.")
            return None

        # Безопасно извлекаем торговое название
        trade_name = h1_tag.contents[0].strip() if h1_tag.contents and isinstance(h1_tag.contents[0], str) else "Название не найдено"

        # Безопасно извлекаем МНН
        medication_name_tag = h1_tag.find('span', class_='mnn')
        medication_name = medication_name_tag.text.strip().capitalize() if medication_name_tag and medication_name_tag.text else trade_name.capitalize()
        
        # Безопасно извлекаем фарм. группу
        group_header = soup.find(string=re.compile(r'Клинико-фармакологическая группа:'))
        group_name = group_header.find_next(string=True).strip() if group_header and group_header.find_next(string=True) else "Не указана"

        # Безопасно извлекаем форму выпуска
        release_form_tag = h1_tag.find('span', class_='ext')
        release_form = release_form_tag.text.strip() if release_form_tag and release_form_tag.text else "Не указана"

        medication_data = {
            'medication_name': medication_name,
            'trade_names': [{
                'name': trade_name,
                'group': group_name,
                'release_form': release_form
            }],
            'regimens': []
        }

        # --- Улучшенное извлечение схем дозирования ---
        dosage_div = soup.find('div', attrs={'colref': 'Dosage'})
        if dosage_div:
            # Вместо сложного анализа, который может сломаться,
            # мы извлекаем весь текст из блока дозирования.
            # Это надежно и гарантирует, что никакая информация не будет потеряна.
            all_notes = ' '.join(dosage_div.stripped_strings)
            
            medication_data['regimens'].append({
                'name': 'Общая схема дозирования',
                'notes': all_notes,
                'population_criteria': [],
                'dosing_instructions': [],
                'adjustments': []
            })
        
        return medication_data

    except Exception as e:
        print(f"  ОШИБКА при анализе файла {os.path.basename(file_path)}: {e}")
        return None

def run():
    """Основная функция для запуска скрипта."""
    all_medications_data = []

    if not os.path.exists(SOURCE_HTML_DIR):
        print(f"ОШИБКА: Директория с исходными файлами не найдена: {SOURCE_HTML_DIR}")
        return

    print(f"Начинаю сканирование директории: {SOURCE_HTML_DIR}")
    
    # Проходим по всем файлам в директории
    for filename in os.listdir(SOURCE_HTML_DIR):
        if filename.endswith(('.html', '.htm')):
            file_path = os.path.join(SOURCE_HTML_DIR, filename)
            
            # Анализируем каждый файл и добавляем результат в общий список
            data = parse_html_file(file_path)
            if data:
                all_medications_data.append(data)

    if not all_medications_data:
        print("Не найдено данных для генерации YAML файла.")
        return

    # Записываем все собранные данные в один YAML файл
    print(f"\nНайдена информация по {len(all_medications_data)} препаратам.")
    print(f"Сохраняю результат в файл: {OUTPUT_YAML_FILE}")
    try:
        with open(OUTPUT_YAML_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(all_medications_data, f, allow_unicode=True, sort_keys=False, indent=2)
        print("Генерация YAML файла успешно завершена! ✅")
    except Exception as e:
        print(f"ОШИБКА при записи YAML файла: {e}")