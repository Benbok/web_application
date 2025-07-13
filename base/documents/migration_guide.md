# Руководство по миграциям для модуля Documents

## Обзор изменений

После внесения улучшений в модуль Documents необходимо выполнить миграции базы данных для добавления новых полей и моделей.

## Шаги для выполнения миграций

### 1. Подготовка к миграции

Перед выполнением миграций убедитесь, что:

1. **Создана резервная копия базы данных**
   ```bash
   python manage.py dumpdata > backup_before_migration.json
   ```

2. **Проверены зависимости**
   ```bash
   pip install django-redis  # для кэширования
   pip install reportlab     # для экспорта PDF (опционально)
   pip install python-docx   # для экспорта DOCX (опционально)
   ```

### 2. Выполнение миграций

#### Шаг 1: Создание миграции
```bash
cd base
python manage.py makemigrations documents
```

#### Шаг 2: Проверка миграции
```bash
python manage.py showmigrations documents
```

#### Шаг 3: Выполнение миграции
```bash
python manage.py migrate documents
```

### 3. Обновление существующих данных

После выполнения миграции может потребоваться обновить существующие данные:

#### Обновление статусов документов
```python
# В Django shell (python manage.py shell)
from documents.models import ClinicalDocument

# Устанавливаем is_archived = False для существующих документов
ClinicalDocument.objects.filter(is_archived__isnull=True).update(is_archived=False)

# Устанавливаем is_active = True для существующих типов документов
from documents.models import DocumentType
DocumentType.objects.filter(is_active__isnull=True).update(is_active=True)

# Устанавливаем is_active = True для существующих шаблонов
from documents.models import DocumentTemplate
DocumentTemplate.objects.filter(is_active__isnull=True).update(is_active=True)
```

#### Создание поисковых векторов (для PostgreSQL)
```python
# В Django shell
from documents.models import ClinicalDocument
from documents.optimizations import DocumentSearch

# Обновляем поисковые векторы для существующих документов
for document in ClinicalDocument.objects.all():
    document.data_search = DocumentSearch.create_search_vector(document)
    document.save(update_fields=['data_search'])
```

### 4. Настройка кэша

#### Добавление настроек кэша в settings.py
```python
# settings.py

# Настройки кэша
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Использование кэша для сессий (опционально)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

#### Установка Redis (если не установлен)
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis

# Windows
# Скачать с https://redis.io/download
```

### 5. Создание индексов (для PostgreSQL)

Если используется PostgreSQL, создайте дополнительные индексы:

```sql
-- Подключитесь к базе данных и выполните:

-- GIN индекс для JSON-поля data
CREATE INDEX CONCURRENTLY IF NOT EXISTS document_data_gin_idx 
ON documents_clinicaldocument USING GIN (data);

-- GIN индекс для поискового вектора
CREATE INDEX CONCURRENTLY IF NOT EXISTS document_search_gin_idx 
ON documents_clinicaldocument USING GIN (data_search);

-- Индекс для поиска по типу документа и дате
CREATE INDEX CONCURRENTLY IF NOT EXISTS document_type_date_idx 
ON documents_clinicaldocument (document_type_id, datetime_document);

-- Индекс для поиска по автору
CREATE INDEX CONCURRENTLY IF NOT EXISTS document_author_idx 
ON documents_clinicaldocument (author_id);

-- Индекс для поиска по статусам
CREATE INDEX CONCURRENTLY IF NOT EXISTS document_status_idx 
ON documents_clinicaldocument (is_signed, is_canceled, is_archived);
```

### 6. Обновление кода

#### Обновление импортов в views.py
```python
# Замените старые импорты на новые
from .forms_improved import build_document_form
from .services import DocumentService, DocumentTemplateService
```

#### Обновление URL-ов в главном urls.py
```python
# В главном urls.py проекта
from documents.urls_improved import urlpatterns as documents_urls

urlpatterns = [
    # ... другие URL-ы
    path('documents/', include(documents_urls)),
]
```

### 7. Тестирование

После выполнения всех миграций протестируйте:

1. **Создание документов**
   ```bash
   python manage.py runserver
   # Откройте браузер и попробуйте создать документ
   ```

2. **Поиск документов**
   - Перейдите на страницу поиска
   - Попробуйте различные фильтры

3. **Действия с документами**
   - Подписание
   - Аннулирование
   - Архивирование

4. **Кэширование**
   - Проверьте, что формы загружаются быстрее при повторных запросах

### 8. Мониторинг

#### Проверка логов
```bash
# Проверьте логи Django
tail -f logs/django.log

# Проверьте логи Redis
redis-cli monitor
```

#### Проверка производительности
```python
# В Django shell
from django.core.cache import cache
from documents.optimizations import DocumentOptimizations

# Проверьте кэш
cache.get('document_form_test')
```

## Возможные проблемы и решения

### 1. Ошибка при создании индексов
**Проблема**: `ERROR: relation "documents_clinicaldocument" does not exist`

**Решение**: Убедитесь, что миграции выполнены:
```bash
python manage.py migrate
```

### 2. Ошибка подключения к Redis
**Проблема**: `ConnectionError: Error 111 connecting to localhost:6379`

**Решение**: Запустите Redis:
```bash
sudo systemctl start redis
# или
redis-server
```

### 3. Ошибка импорта модулей
**Проблема**: `ModuleNotFoundError: No module named 'documents.forms_improved'`

**Решение**: Убедитесь, что файлы созданы в правильных директориях и импорты корректны.

### 4. Медленная работа после миграции
**Проблема**: Документы загружаются медленно

**Решение**: 
- Проверьте, что индексы созданы
- Убедитесь, что кэш работает
- Проверьте настройки `select_related` и `prefetch_related`

## Откат изменений (если необходимо)

Если потребуется откатить изменения:

```bash
# Откат миграции
python manage.py migrate documents 0002_initial

# Восстановление данных из резервной копии
python manage.py loaddata backup_before_migration.json
```

## Заключение

После выполнения всех шагов модуль Documents будет полностью обновлен с новыми функциями:

- ✅ Кэширование форм
- ✅ Оптимизированные запросы к БД
- ✅ Система версионирования
- ✅ Аудит действий
- ✅ Расширенный поиск
- ✅ Статистика и аналитика
- ✅ API для действий

Модуль готов к использованию в продакшене! 