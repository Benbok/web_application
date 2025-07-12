# Оптимизированная архитектура модуля Encounters

## Обзор

Этот документ описывает реализацию оптимизированной архитектуры для модуля `encounters`, которая следует принципам SOLID и использует современные паттерны проектирования.

## Структура оптимизированной архитектуры

```
encounters/
├── models.py                    # Модели данных
├── views.py                     # Оригинальные представления
├── views_optimized.py           # Оптимизированные представления
├── forms.py                     # Формы
├── admin.py                     # Админ-панель
├── services/                    # Слой сервисов
│   ├── __init__.py
│   └── encounter_service.py     # Основной сервис
├── repositories/                # Слой репозиториев
│   ├── __init__.py
│   └── encounter_repository.py  # Репозиторий данных
├── factories/                   # Фабрики объектов
│   ├── __init__.py
│   └── encounter_factory.py     # Фабрика случаев обращения
├── events/                      # Система событий
│   ├── __init__.py
│   └── encounter_events.py      # События и обработчики
├── strategies/                  # Стратегии исходов
│   ├── __init__.py
│   └── outcome_strategies.py    # Стратегии для исходов
├── examples/                    # Примеры использования
│   ├── __init__.py
│   └── usage_examples.py       # Примеры использования
└── README.md                    # Основная документация
```

## Ключевые компоненты

### 1. Service Layer (Слой сервисов)

**Файл**: `services/encounter_service.py`

**Назначение**: Инкапсуляция бизнес-логики и операций с случаями обращения.

**Основные возможности**:
- Закрытие случаев обращения
- Возврат случаев в активное состояние
- Архивирование и восстановление
- Валидация данных
- Синхронизация с другими модулями

**Пример использования**:
```python
from encounters.services.encounter_service import EncounterService

# Создание сервиса
service = EncounterService(encounter)

# Закрытие случая
service.close_encounter('consultation_end')

# Возврат в активное состояние
service.reopen_encounter()

# Получение деталей
details = service.get_encounter_details()
```

### 2. Repository Pattern (Паттерн репозитория)

**Файл**: `repositories/encounter_repository.py`

**Назначение**: Абстракция доступа к данным и оптимизация запросов.

**Основные возможности**:
- Оптимизированные запросы с `select_related` и `prefetch_related`
- Специализированные методы для различных сценариев
- Статистика и аналитика
- Массовые операции

**Пример использования**:
```python
from encounters.repositories.encounter_repository import EncounterRepository

repository = EncounterRepository()

# Получение случая с документами
encounter = repository.get_with_documents(encounter_id)

# Получение статистики
stats = repository.get_encounters_statistics()

# Получение случаев пациента
patient_encounters = repository.get_by_patient(patient)
```

### 3. Factory Pattern (Паттерн фабрики)

**Файл**: `factories/encounter_factory.py`

**Назначение**: Создание объектов с различными конфигурациями.

**Основные возможности**:
- Создание базовых случаев обращения
- Создание случаев с переводами
- Создание случаев с документами
- Создание тестовых данных
- Массовое создание

**Пример использования**:
```python
from encounters.factories.encounter_factory import EncounterFactory

# Создание базового случая
encounter = EncounterFactory.create_encounter(patient, doctor)

# Создание случая с переводом
transfer_encounter = EncounterFactory.create_transfer_encounter(
    patient, doctor, department
)

# Создание тестового случая
test_encounter = EncounterFactory.create_test_encounter()
```

### 4. Event System (Система событий)

**Файл**: `events/encounter_events.py`

**Назначение**: Централизованная система событий для автоматической синхронизации между модулями.

**Основные возможности**:
- Автоматическая публикация событий при операциях
- Обработчики событий для различных действий
- Синхронизация с appointments и departments
- Логирование всех операций
- Расширяемость через регистрацию новых обработчиков

**Пример использования**:
```python
from encounters.events.encounter_events import event_bus, EncounterClosedEvent

# Регистрация пользовательского обработчика
class CustomEventHandler:
    def handle(self, event):
        print(f"Обработано событие: {event.get_description()}")

event_bus.register_handler("encounter_closed", CustomEventHandler())

# События публикуются автоматически при операциях
service = EncounterService(encounter)
service.close_encounter('consultation_end')  # Событие опубликовано автоматически
```

### 5. Strategy Pattern (Паттерн стратегии)

**Файл**: `strategies/outcome_strategies.py`

**Назначение**: Обработка различных исходов encounters через стратегии.

**Основные возможности**:
- Различные стратегии для разных исходов
- Валидация требований для каждого исхода
- Легкое добавление новых типов исходов
- Централизованная обработка логики исходов

**Пример использования**:
```python
from encounters.strategies.outcome_strategies import OutcomeProcessor, OutcomeStrategyFactory

# Получение доступных исходов
available_outcomes = OutcomeStrategyFactory.get_available_outcomes()

# Обработка исхода через стратегию
processor = OutcomeProcessor(encounter)
success = processor.process_outcome('consultation_end', user=doctor)

# Получение требований для исхода
requirements = processor.get_outcome_requirements('transferred')
print(f"Обязательные поля: {requirements['required_fields']}")
```

### 6. Optimized Views (Оптимизированные представления)

**Файл**: `views_optimized.py`

**Назначение**: Представления, использующие новую архитектуру.

**Основные улучшения**:
- Использование сервисов вместо прямой логики
- Использование репозиториев для доступа к данным
- Улучшенная обработка ошибок
- Более чистый и читаемый код

## Преимущества оптимизированной архитектуры

### 1. Улучшенная тестируемость

**До оптимизации**:
```python
# Сложно тестировать из-за смешивания логики
def close_encounter(self, outcome, transfer_department=None):
    if not self.documents.exists():
        raise ValueError("Нет документов")
    # Много логики в одном методе
```

**После оптимизации**:
```python
# Легко тестировать каждый компонент отдельно
service = EncounterService(encounter)
service.close_encounter('consultation_end')

# Можно легко мокать зависимости
mock_service = Mock(spec=EncounterService)
```

### 2. Уменьшенная связанность

**До оптимизации**:
```python
# Прямые зависимости между модулями
from departments.models import PatientDepartmentStatus
from appointments.models import AppointmentStatus
```

**После оптимизации**:
```python
# Абстракции через сервисы
service = EncounterService(encounter)
service.close_encounter(outcome, department)
# Сервис сам управляет зависимостями
```

### 3. Повышенная расширяемость

**До оптимизации**:
```python
# Сложно добавить новые исходы
OUTCOME_CHOICES = [
    ('consultation_end', 'Консультация'),
    ('transferred', 'Перевод в отделение'),
]
```

**После оптимизации**:
```python
# Легко добавить новые стратегии
class NewOutcomeStrategy(OutcomeStrategy):
    def get_outcome_code(self) -> str:
        return 'new_outcome'
    
    def validate(self, **kwargs) -> bool:
        # Валидация для нового исхода
        return True
    
    def execute(self, **kwargs) -> bool:
        # Логика для нового исхода
        return True

# Регистрация новой стратегии
OutcomeStrategyFactory.register_strategy('new_outcome', NewOutcomeStrategy)
```

### 4. Улучшенная производительность

**До оптимизации**:
```python
# N+1 проблема
for encounter in encounters:
    print(encounter.patient.full_name)  # Дополнительный запрос
```

**После оптимизации**:
```python
# Оптимизированные запросы
repository = EncounterRepository()
encounters = repository.get_with_related_data(encounter_id)
# Один запрос с select_related
```

## Миграция с старой архитектуры

### Пошаговый план миграции:

1. **Этап 1**: Внедрение сервисов
   ```python
   # Старый код
   encounter.close_encounter('consultation_end')
   
   # Новый код
   service = EncounterService(encounter)
   service.close_encounter('consultation_end')
   ```

2. **Этап 2**: Использование репозиториев
   ```python
   # Старый код
   encounters = Encounter.objects.filter(patient=patient)
   
   # Новый код
   repository = EncounterRepository()
   encounters = repository.get_by_patient(patient)
   ```

3. **Этап 3**: Использование фабрик
   ```python
   # Старый код
   encounter = Encounter.objects.create(patient=patient, doctor=doctor)
   
   # Новый код
   encounter = EncounterFactory.create_encounter(patient, doctor)
   ```

4. **Этап 4**: Обновление представлений
   ```python
   # Заменить views.py на views_optimized.py
   from .views_optimized import EncounterDetailView
   ```

## Примеры использования

### Базовые операции

```python
from encounters.services.encounter_service import EncounterService
from encounters.repositories.encounter_repository import EncounterRepository
from encounters.factories.encounter_factory import EncounterFactory

# Создание
encounter = EncounterFactory.create_encounter(patient, doctor)

# Работа с сервисом
service = EncounterService(encounter)
service.close_encounter('consultation_end')

# Работа с репозиторием
repository = EncounterRepository()
stats = repository.get_encounters_statistics()
```

### Сложные сценарии

```python
# Полный жизненный цикл
encounter = EncounterFactory.create_encounter(patient, doctor)
service = EncounterService(encounter)

# Добавление документов
document = ClinicalDocument.objects.create(
    content_type=encounter.get_content_type(),
    object_id=encounter.id,
    document_type=document_type,
    data={'symptoms': 'Головная боль'}
)

# Закрытие с переводом (событие опубликовано автоматически)
service.close_encounter('transferred', department, user=doctor)

# Возврат в активное состояние (событие опубликовано автоматически)
service.reopen_encounter(user=doctor)

# Архивирование (событие опубликовано автоматически)
service.archive_encounter(user=doctor)

# Использование стратегий
processor = OutcomeProcessor(encounter)
available_outcomes = OutcomeStrategyFactory.get_available_outcomes()
requirements = processor.get_outcome_requirements('transferred')
```

### Массовые операции

```python
# Создание нескольких случаев
patients = Patient.objects.all()[:5]
encounters = EncounterFactory.create_encounter_batch(
    patients=patients,
    doctor=doctor
)

# Получение статистики
repository = EncounterRepository()
stats = repository.get_encounters_statistics()
print(f"Всего случаев: {stats['total']}")
```

## Тестирование

### Unit тесты для сервисов

```python
from django.test import TestCase
from encounters.services.encounter_service import EncounterService

class EncounterServiceTest(TestCase):
    def setUp(self):
        self.encounter = EncounterFactory.create_test_encounter()
        self.service = EncounterService(self.encounter)
    
    def test_close_encounter_without_documents(self):
        with self.assertRaises(EncounterValidationError):
            self.service.close_encounter('consultation_end')
    
    def test_close_encounter_with_documents(self):
        # Добавляем документ
        ClinicalDocument.objects.create(
            content_type=self.encounter.get_content_type(),
            object_id=self.encounter.id,
            document_type=document_type,
            data={'symptoms': 'Test'}
        )
        
        result = self.service.close_encounter('consultation_end')
        self.assertTrue(result)
        self.assertFalse(self.encounter.is_active)
```

### Integration тесты

```python
class EncounterIntegrationTest(TestCase):
    def test_full_lifecycle(self):
        # Создание
        encounter = EncounterFactory.create_encounter(patient, doctor)
        
        # Добавление документов
        document = ClinicalDocument.objects.create(...)
        
        # Закрытие
        service = EncounterService(encounter)
        service.close_encounter('consultation_end')
        
        # Проверка состояния
        self.assertFalse(encounter.is_active)
        self.assertEqual(encounter.outcome, 'consultation_end')
```

## Производительность

### Оптимизация запросов

**До оптимизации**:
```python
# N+1 проблема
encounters = Encounter.objects.all()
for encounter in encounters:
    print(encounter.patient.full_name)  # Дополнительный запрос для каждого
```

**После оптимизации**:
```python
# Оптимизированный запрос
repository = EncounterRepository()
encounters = repository.get_with_related_data(encounter_id)
# Один запрос с select_related
```

### Кэширование

```python
# В репозитории можно добавить кэширование
from django.core.cache import cache

def get_encounters_statistics(self):
    cache_key = 'encounters_statistics'
    stats = cache.get(cache_key)
    
    if stats is None:
        stats = self._calculate_statistics()
        cache.set(cache_key, stats, 300)  # Кэш на 5 минут
    
    return stats
```

## Мониторинг и логирование

### Логирование операций

```python
import logging

logger = logging.getLogger(__name__)

class EncounterService:
    def close_encounter(self, outcome, transfer_department=None):
        logger.info(f"Закрытие случая {self.encounter.id} с исходом {outcome}")
        
        try:
            # Логика закрытия
            result = self._perform_close(outcome, transfer_department)
            logger.info(f"Случай {self.encounter.id} успешно закрыт")
            return result
        except Exception as e:
            logger.error(f"Ошибка при закрытии случая {self.encounter.id}: {e}")
            raise
```

### Метрики производительности

```python
import time
from django.db import connection

class EncounterRepository:
    def get_with_related_data(self, encounter_id):
        start_time = time.time()
        
        result = Encounter.objects.select_related(
            'patient', 'doctor', 'transfer_to_department'
        ).prefetch_related('documents').get(id=encounter_id)
        
        execution_time = time.time() - start_time
        logger.info(f"Запрос выполнен за {execution_time:.3f} секунд")
        
        return result
```

## Заключение

Оптимизированная архитектура модуля `encounters` предоставляет:

1. **Лучшую тестируемость** - изолированные компоненты
2. **Меньшую связанность** - абстракции и интерфейсы
3. **Большую расширяемость** - паттерны проектирования
4. **Улучшенную производительность** - оптимизированные запросы
5. **Лучшую поддерживаемость** - четкое разделение ответственности

Эта архитектура следует современным принципам разработки и обеспечивает масштабируемость системы. 