# Детальная документация методов модуля Appointments

## Модели (Models)

### Schedule

#### `doctor_full_name` (property)
**Назначение**: Получение полного имени врача для расписания
**Возвращает**: `str` - полное имя врача или `None`
**Логика**: 
- Проверяет наличие `doctor_profile` у пользователя
- Возвращает `full_name` из профиля врача
- Возвращает `None` если профиль отсутствует

#### `__str__()`
**Назначение**: Строковое представление расписания
**Возвращает**: `str` - форматированная строка с информацией о расписании
**Формат**: "Расписание {ФИО врача} ({время начала}—{время окончания}, {длительность} мин)"
**Пример**: "Расписание Иванов И.И. (09:00—17:00, 30 мин)"

#### `clean()`
**Назначение**: Валидация и автоматическая корректировка времени окончания смены
**Логика**:
- Вычисляет общее количество минут в смене
- Рассчитывает количество слотов на основе длительности приема
- Корректирует время окончания смены для точного соответствия слотам
**Пример**: Смена 09:00-17:00 с длительностью 30 мин → окончание 17:00 (ровно 16 слотов)

### AppointmentEvent

#### `doctor` (property)
**Назначение**: Безопасный доступ к врачу через расписание
**Возвращает**: `User` - объект врача или `None`
**Логика**: Возвращает врача из связанного расписания, если оно существует

#### `__str__()`
**Назначение**: Строковое представление записи на прием
**Возвращает**: `str` - форматированная строка с информацией о записи
**Формат**: "Прием у врача {ФИО врача} для {ФИО пациента} в {дата/время}"
**Пример**: "Прием у врача Иванов И.И. для Петров П.П. в 2024-01-15 10:00:00"

#### `is_upcoming()`
**Назначение**: Проверка, является ли прием предстоящим
**Возвращает**: `bool` - True если прием в будущем, False если в прошлом
**Логика**: Сравнивает время начала приема с текущим временем

#### `is_completed()`
**Назначение**: Проверка завершенности приема
**Возвращает**: `bool` - True если статус "completed", False иначе
**Логика**: Проверяет равенство статуса `AppointmentStatus.COMPLETED`

#### `archive()`
**Назначение**: Архивирование записи с синхронизацией encounter
**Логика**:
- Проверяет наличие связанного encounter
- Если encounter существует и не архивирован - архивирует его
- Вызывает родительский метод archive()
**Использование**: `appointment.archive()`

#### `unarchive()`
**Назначение**: Восстановление из архива с синхронизацией encounter
**Логика**:
- Проверяет наличие связанного encounter
- Если encounter архивирован - восстанавливает его
- Вызывает родительский метод unarchive()
**Использование**: `appointment.unarchive()`

## Сервисы (Services)

### `generate_available_slots(start_dt, end_dt, doctor_id)`
**Назначение**: Генерация свободных слотов по расписанию врача
**Параметры**:
- `start_dt` (datetime) - начало периода поиска
- `end_dt` (datetime) - конец периода поиска  
- `doctor_id` (int) - ID врача
**Возвращает**: `list` - список словарей с данными слотов
**Структура возвращаемых данных**:
```python
[
    {
        "title": "Свободно",
        "start": "2024-01-15T10:00:00+03:00",
        "end": "2024-01-15T10:30:00+03:00", 
        "color": "#28a745",
        "extendedProps": {"schedule_id": 1}
    }
]
```
**Логика**:
1. Получает все расписания врача
2. Получает список забронированных слотов
3. Для каждого расписания генерирует слоты на основе повторений
4. Исключает уже забронированные времена
5. Возвращает список свободных слотов

## Представления (Views)

### AppointmentEventViewSet
**Назначение**: REST API для управления записями на прием
**Методы**: GET, POST, PUT, PATCH, DELETE
**Фильтрация**: Поддерживает фильтр по `doctor` через query параметр

#### `get_queryset()`
**Назначение**: Получение queryset с возможностью фильтрации
**Логика**: Добавляет фильтр по врачу если передан параметр `doctor`

### AppointmentEventsAPI
**Назначение**: API для FullCalendar - возвращает записанные приемы
**Метод**: GET
**Возвращает**: JSON с событиями для календаря

#### `get()`
**Логика**:
1. Получает записи со статусом "scheduled"
2. Форматирует ФИО пациента (Фамилия И.О.)
3. Создает события для календаря с цветовой индикацией
4. Возвращает JSON массив событий

### AvailableSlotsAPIView
**Назначение**: API для получения свободных слотов врача
**Метод**: GET
**Параметры**: `start`, `end`, `doctor_id`

#### `get()`
**Логика**:
1. Валидирует обязательные параметры
2. Парсит даты из строк
3. Вызывает `generate_available_slots()`
4. Возвращает результат в формате JSON

### AppointmentCreateView
**Назначение**: Создание новой записи на прием
**Метод**: GET, POST

#### `get_initial()`
**Назначение**: Подготовка начальных данных для формы
**Логика**:
1. Проверяет параметры в сессии (после создания пациента)
2. Проверяет параметры в URL
3. Заполняет начальные значения формы
**Поддерживаемые параметры**:
- `schedule` - ID расписания
- `start` - время начала приема
- `patient` - ID пациента

### CreateEncounterForAppointmentView
**Назначение**: Создание случая обращения для записи
**Метод**: POST
**Параметр**: `pk` - ID записи на прием

#### `post()`
**Логика**:
1. Получает запись на прием по ID
2. Проверяет отсутствие связанного encounter
3. Создает новый Encounter с данными из записи
4. Связывает encounter с записью
5. Перенаправляет к деталям encounter

## Формы (Forms)

### AppointmentEventForm
**Назначение**: Форма создания/редактирования записи на прием
**Поля**: schedule, patient, start, notes, status

#### `clean()`
**Назначение**: Валидация данных формы
**Логика**:
1. Вычисляет время окончания приема
2. Проверяет время приема в рамках смены врача
3. Проверяет отсутствие пересечений у врача
4. Проверяет отсутствие пересечений у пациента
**Возвращает**: `cleaned_data` или вызывает `ValidationError`

### ScheduleAdminForm
**Назначение**: Форма для админ-панели расписаний

#### `__init__()`
**Назначение**: Настройка отображения врачей в выпадающем списке
**Логика**: Устанавливает `label_from_instance` для поля doctor

## Сериализаторы (Serializers)

### AppointmentEventSerializer
**Назначение**: Сериализация записи на прием
**Поля**: id, schedule, patient, start, end, notes, status, title

#### `get_title()`
**Назначение**: Форматирование ФИО пациента для отображения
**Параметр**: `obj` - объект AppointmentEvent
**Возвращает**: `str` - отформатированное ФИО
**Логика**: Преобразует полное имя в формат "Фамилия И.О."

## Админ-панель (Admin)

### ScheduleAdmin

#### `get_queryset()`
**Назначение**: Оптимизация запросов для админ-панели
**Возвращает**: Queryset с select_related для doctor и doctor_profile

#### `doctor_full_name()`
**Назначение**: Отображение полного имени врача в списке
**Возвращает**: `str` - полное имя врача или "—"
**Логика**: Получает full_name из doctor_profile

### AppointmentEventAdmin

#### `archive_selected()`
**Назначение**: Массовое архивирование записей
**Логика**: Вызывает `archive()` для каждой выбранной записи
**Сообщение**: Уведомляет о количестве архивированных записей

#### `unarchive_selected()`
**Назначение**: Массовое восстановление записей из архива
**Логика**: Сбрасывает флаги архивирования для выбранных записей
**Сообщение**: Уведомляет о количестве восстановленных записей

#### `get_queryset()`
**Назначение**: Получение всех записей включая архивированные
**Возвращает**: Queryset через `all_objects`

#### `doctor_full_name()`
**Назначение**: Отображение полного имени врача в списке
**Возвращает**: `str` - полное имя врача или "—"
**Логика**: Получает full_name из doctor_profile

## Примеры использования

### Создание записи на прием
```python
# Создание расписания
schedule = Schedule.objects.create(
    doctor=doctor,
    start_time=time(9, 0),
    end_time=time(17, 0),
    duration=30
)

# Создание записи
appointment = AppointmentEvent.objects.create(
    schedule=schedule,
    patient=patient,
    start=datetime(2024, 1, 15, 10, 0),
    status=AppointmentStatus.SCHEDULED
)
```

### Получение свободных слотов
```python
from .services import generate_available_slots

slots = generate_available_slots(
    start_dt=datetime(2024, 1, 15),
    end_dt=datetime(2024, 1, 16),
    doctor_id=1
)
```

### Архивирование записи
```python
appointment = AppointmentEvent.objects.get(id=1)
appointment.archive()  # Также архивирует связанный encounter
```

### Проверка статуса приема
```python
if appointment.is_upcoming():
    print("Прием еще не состоялся")
    
if appointment.is_completed():
    print("Прием завершен")
``` 