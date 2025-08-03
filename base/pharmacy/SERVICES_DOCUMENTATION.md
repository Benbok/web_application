# Документация сервисов Pharmacy

## Обзор

Сервисы в приложении `pharmacy` предоставляют бизнес-логику для работы с препаратами, схемами применения и рекомендациями для пациентов. Архитектура основана на принципах Domain-Driven Design с четким разделением ответственности.

## Структура сервисов

### 1. MedicationService
Сервис для работы с препаратами и торговыми наименованиями.

#### Методы:

**`get_medications_by_group(group_id: Optional[int] = None) -> List[Dict]`**
- Получает список препаратов, сгруппированных по фармакологическим группам
- Если указан `group_id`, возвращает только препараты из этой группы
- Возвращает расширенную информацию о каждом препарате

**`search_medications(query: str) -> List[Dict]`**
- Поиск препаратов по торговому названию или МНН
- Ограничивает результаты до 20 записей
- Поддерживает нечеткий поиск (case-insensitive)

#### Пример использования:
```python
from pharmacy.services import MedicationService

# Получить все препараты
all_medications = MedicationService.get_medications_by_group()

# Получить препараты конкретной группы
antibiotics = MedicationService.get_medications_by_group(group_id=1)

# Поиск препаратов
results = MedicationService.search_medications("амоксициллин")
```

### 2. RegimenService
Сервис для работы со схемами применения препаратов.

#### Методы:

**`get_regimens_for_medication(medication_id: int) -> List[Dict]`**
- Получает все схемы применения для конкретного препарата
- Включает полную информацию о показаниях, критериях пациентов, дозировках и корректировках
- Оптимизирован для минимизации запросов к БД

**`get_regimens_by_diagnosis(diagnosis_id: int) -> List[Dict]`**
- Получает схемы применения для конкретного диагноза
- Возвращает упрощенную информацию о схемах

#### Пример использования:
```python
from pharmacy.services import RegimenService

# Получить схемы для препарата
regimens = RegimenService.get_regimens_for_medication(medication_id=1)

# Получить схемы для диагноза
diagnosis_regimens = RegimenService.get_regimens_by_diagnosis(diagnosis_id=5)
```

### 3. PatientRecommendationService
Сервис для подбора персонализированных рекомендаций по препаратам.

#### Методы:

**`get_patient_recommendations(patient, diagnosis=None, exclude_medication_ids=None) -> Dict`**
- Подбирает подходящие схемы применения для конкретного пациента
- Учитывает возраст, вес, диагноз и аллергии
- Возвращает рекомендации, сгруппированные по препаратам

**`_is_patient_suitable(criteria, age_in_days, weight_kg) -> bool`** (приватный)
- Проверяет соответствие пациента критериям схемы применения

#### Логика подбора рекомендаций:
1. **Расчет параметров пациента**: возраст в днях, вес
2. **Фильтрация по диагнозу**: если указан диагноз, выбираются только соответствующие схемы
3. **Исключение аллергенов**: исключаются препараты, на которые у пациента аллергия
4. **Проверка критериев**: для каждой схемы проверяется соответствие пациента критериям (возраст, вес)
5. **Формирование рекомендаций**: создается структурированный ответ с полной информацией

#### Пример использования:
```python
from pharmacy.services import PatientRecommendationService
from patients.models import Patient
from diagnosis.models import Diagnosis

# Получить пациента и диагноз
patient = Patient.objects.get(id=1)
diagnosis = Diagnosis.objects.get(id=5)

# Получить рекомендации
recommendations = PatientRecommendationService.get_patient_recommendations(
    patient=patient,
    diagnosis=diagnosis,
    exclude_medication_ids=[10, 15]  # ID препаратов с аллергией
)
```

### 4. ReferenceDataService
Сервис для работы со справочными данными.

#### Методы:

**`get_medication_groups() -> List[Dict]`**
- Получает список всех фармакологических групп
- Включает количество препаратов в каждой группе

**`get_release_forms() -> List[Dict]`**
- Получает список всех форм выпуска
- Включает количество препаратов в каждой форме

**`get_administration_methods() -> List[Dict]`**
- Получает список всех способов введения

#### Пример использования:
```python
from pharmacy.services import ReferenceDataService

# Получить справочные данные
groups = ReferenceDataService.get_medication_groups()
forms = ReferenceDataService.get_release_forms()
methods = ReferenceDataService.get_administration_methods()
```

## Структура данных

### Рекомендации для пациента
```python
{
    "Название препарата (МНН)": [
        {
            "regimen_id": 1,
            "regimen_name": "Стандартная терапия для взрослых",
            "medication_name": "Амоксициллин",
            "notes": "Общие примечания к схеме",
            "suitable_criteria": [
                {
                    "name": "Взрослые и дети > 12 лет",
                    "age_range": "4380 - ∞ дней",
                    "weight_range": "40.0 - ∞ кг"
                }
            ],
            "dosing_instructions": [
                {
                    "dose_type": "Поддерживающая",
                    "dose_description": "500 мг",
                    "frequency": "3 раза в сутки",
                    "duration": "7-10 дней",
                    "route": "Перорально"
                }
            ],
            "adjustments": [
                {
                    "condition": "При КК от 21 до 60 мл/мин",
                    "adjustment": "суточную дозу следует уменьшить на 25%"
                }
            ]
        }
    ]
}
```

## Оптимизация производительности

### Использование select_related и prefetch_related
Все сервисы оптимизированы для минимизации количества запросов к БД:

```python
# Пример оптимизации в RegimenService
regimens = Regimen.objects.filter(medication_id=medication_id).prefetch_related(
    'indications',
    'population_criteria', 
    'dosing_instructions',
    'adjustments'
)
```

### Кэширование справочных данных
Для часто используемых справочных данных рекомендуется использовать кэширование:

```python
from django.core.cache import cache

def get_medication_groups():
    cache_key = 'medication_groups'
    groups = cache.get(cache_key)
    if groups is None:
        groups = MedicationGroup.objects.all()
        cache.set(cache_key, groups, 3600)  # Кэш на 1 час
    return groups
```

## Обратная совместимость

Для обеспечения обратной совместимости сохранена функция `get_medication_recommendations()`, которая теперь является оберткой над `PatientRecommendationService.get_patient_recommendations()`.

## Расширение функциональности

### Добавление новых методов
При добавлении новых методов в сервисы следуйте принципам:

1. **Единая ответственность**: каждый метод должен выполнять одну конкретную задачу
2. **Типизация**: используйте type hints для всех параметров и возвращаемых значений
3. **Документация**: добавляйте подробные docstrings
4. **Оптимизация**: используйте select_related/prefetch_related для оптимизации запросов

### Пример добавления нового метода:
```python
class MedicationService:
    @staticmethod
    def get_medications_by_atc_code(atc_code: str) -> List[Dict]:
        """
        Получает препараты по АТХ коду.
        
        :param atc_code: АТХ код для поиска
        :return: Список препаратов с указанным АТХ кодом
        """
        queryset = TradeName.objects.filter(
            atc_code__startswith=atc_code
        ).select_related('medication', 'medication_group')
        
        return [
            {
                'id': tn.id,
                'trade_name': tn.name,
                'medication_name': tn.medication.name,
                'atc_code': tn.atc_code,
                'group': tn.medication_group.name if tn.medication_group else None
            }
            for tn in queryset
        ]
``` 