# Документация методов модуля Encounters

## Модель Encounter

### Методы жизненного цикла

#### `close_encounter(outcome, transfer_department=None)`
**Назначение**: Закрытие случая обращения с указанием исхода
**Параметры**:
- `outcome` (str) - Исход обращения ('consultation_end' или 'transferred')
- `transfer_department` (Department, optional) - Отделение для перевода

**Возвращает**: bool - True если случай успешно закрыт, False если уже закрыт

**Логика**:
1. Проверяет наличие документов (требуется минимум один документ)
2. Проверяет активность случая
3. Устанавливает дату завершения (из appointment.end или текущее время)
4. Устанавливает исход обращения
5. При переводе устанавливает отделение

**Исключения**:
- `ValueError` - если нет прикрепленных документов

**Пример использования**:
```python
# Закрытие консультации
if encounter.close_encounter('consultation_end'):
    print("Консультация завершена")

# Закрытие с переводом
if encounter.close_encounter('transferred', cardiology_department):
    print("Пациент переведен в кардиологию")
```

#### `reopen_encounter()`
**Назначение**: Возврат случая обращения в активное состояние
**Параметры**: Нет
**Возвращает**: bool - True если случай успешно возвращен, False если уже активен

**Логика**:
1. Проверяет, что случай не активен
2. При переводе отменяет связанную запись PatientDepartmentStatus
3. Очищает дату завершения, исход и отделение перевода
4. Устанавливает активность в True
5. Синхронизирует статус связанной записи на прием

**Пример использования**:
```python
if encounter.reopen_encounter():
    print("Случай возвращен в активное состояние")
    # Автоматически отменяется перевод в отделение
```

### Методы валидации

#### `clean()`
**Назначение**: Валидация данных модели
**Параметры**: Нет
**Возвращает**: Нет

**Логика**:
- Проверяет, что дата завершения не раньше даты начала

**Исключения**:
- `ValidationError` - если дата завершения раньше даты начала

**Пример использования**:
```python
encounter.date_start = timezone.now()
encounter.date_end = timezone.now() - timedelta(hours=1)
encounter.clean()  # Вызовет ValidationError
```

### Методы сохранения

#### `save(*args, **kwargs)`
**Назначение**: Переопределенный метод сохранения с автоматической логикой
**Параметры**: Стандартные параметры Django Model.save()
**Возвращает**: Нет

**Логика**:
1. Автоматически управляет статусом активности:
   - Если есть дата завершения и исход → `is_active = False`
   - Иначе → `is_active = True`
2. Синхронизирует статус связанной записи на прием:
   - Если случай не активен → статус записи = COMPLETED
   - Если случай активен → статус записи = SCHEDULED

**Пример использования**:
```python
encounter.outcome = 'consultation_end'
encounter.date_end = timezone.now()
encounter.save()  # Автоматически установит is_active = False
```

### Методы архивирования

#### `archive()`
**Назначение**: Архивирование случая обращения с синхронизацией связанных объектов
**Параметры**: Нет
**Возвращает**: Нет

**Логика**:
1. Обнуляет ссылку на Encounter в связанной записи на прием
2. Архивирует все связанные записи PatientDepartmentStatus
3. Вызывает родительский метод archive()

**Пример использования**:
```python
encounter.archive()  # Архивирует случай и связанные объекты
```

#### `unarchive()`
**Назначение**: Восстановление случая обращения из архива
**Параметры**: Нет
**Возвращает**: Нет

**Логика**:
1. Восстанавливает связанную запись на прием (если была архивирована)
2. Восстанавливает все связанные записи PatientDepartmentStatus
3. Вызывает родительский метод unarchive()

**Пример использования**:
```python
encounter.unarchive()  # Восстанавливает случай и связанные объекты
```

### Методы отображения

#### `__str__()`
**Назначение**: Строковое представление случая обращения
**Параметры**: Нет
**Возвращает**: str - Форматированная строка с информацией о случае

**Формат**:
- Если есть исход: "Случай от DD.MM.YYYY — ФИО пациента (Исход)"
- Если нет исхода: "Случай от DD.MM.YYYY — ФИО пациента"

**Пример использования**:
```python
print(encounter)  # "Случай от 15.12.2023 — Иванов И.И. (Консультация)"
```

## Представления (Views)

### EncounterDetailView

#### `get_context_data(**kwargs)`
**Назначение**: Добавление дополнительного контекста для шаблона
**Параметры**: kwargs - стандартные параметры Django
**Возвращает**: dict - Контекст с дополнительными данными

**Добавляемые данные**:
- `documents` - все документы случая
- `encounter_number` - номер обращения для пациента

**Пример использования**:
```python
context = view.get_context_data()
# context['documents'] - список документов
# context['encounter_number'] - номер обращения
```

### EncounterCreateView

#### `setup(request, *args, **kwargs)`
**Назначение**: Инициализация представления с получением пациента
**Параметры**: request, *args, **kwargs
**Возвращает**: Нет

**Логика**:
- Получает пациента по pk из URL параметров
- Сохраняет пациента в self.patient

#### `form_valid(form)`
**Назначение**: Обработка валидной формы с автоматическим заполнением
**Параметры**: form - валидная форма
**Возвращает**: HttpResponseRedirect

**Логика**:
- Устанавливает пациента и врача в форму
- Сохраняет объект
- Перенаправляет к деталям созданного случая

#### `get_context_data(**kwargs)`
**Назначение**: Добавление контекста для шаблона создания
**Параметры**: kwargs
**Возвращает**: dict - Контекст с пациентом и заголовком

#### `get_success_url()`
**Назначение**: URL для перенаправления после успешного создания
**Параметры**: Нет
**Возвращает**: str - URL деталей созданного случая

### EncounterUpdateView

#### `form_valid(form)`
**Назначение**: Обработка валидной формы с дополнительной логикой
**Параметры**: form - валидная форма
**Возвращает**: HttpResponseRedirect

**Логика**:
1. Сохраняет старые значения исхода и отделения
2. Автоматически управляет датой завершения
3. Проверяет наличие документов при закрытии
4. Управляет переводами в отделения:
   - Отменяет старые переводы при изменении
   - Создает новые переводы при необходимости
5. Добавляет сообщения пользователю

#### `get_context_data(**kwargs)`
**Назначение**: Добавление контекста для шаблона редактирования
**Параметры**: kwargs
**Возвращает**: dict - Контекст с пациентом и заголовком

#### `get_success_url()`
**Назначение**: URL для перенаправления после успешного обновления
**Параметры**: Нет
**Возвращает**: str - URL деталей обновленного случая

### EncounterDeleteView

#### `get_context_data(**kwargs)`
**Назначение**: Добавление номера обращения для страницы подтверждения
**Параметры**: kwargs
**Возвращает**: dict - Контекст с номером обращения

#### `get_success_url()`
**Назначение**: URL для перенаправления после удаления
**Параметры**: Нет
**Возвращает**: str - URL деталей пациента

### EncounterCloseView

#### `get_object(queryset=None)`
**Назначение**: Получение объекта с проверкой активности
**Параметры**: queryset - QuerySet (не используется)
**Возвращает**: Encounter - только активные случаи

**Логика**:
- Фильтрует только активные случаи (is_active=True)

#### `get_context_data(**kwargs)`
**Назначение**: Добавление контекста для формы закрытия
**Параметры**: kwargs
**Возвращает**: dict - Контекст с заголовком и номером обращения

#### `form_valid(form)`
**Назначение**: Обработка формы закрытия с созданием переводов
**Параметры**: form - валидная форма
**Возвращает**: HttpResponseRedirect

**Логика**:
1. Получает исход и отделение из формы
2. Вызывает encounter.close_encounter()
3. При переводе создает PatientDepartmentStatus
4. Добавляет сообщения пользователю
5. Перенаправляет к деталям случая

**Исключения**:
- `ValueError` - если нет документов для закрытия

#### `get_success_url()`
**Назначение**: URL для перенаправления после закрытия
**Параметры**: Нет
**Возвращает**: str - URL деталей закрытого случая

### EncounterReopenView

#### `post(request, pk, *args, **kwargs)`
**Назначение**: Обработка POST-запроса для возврата случая в активное состояние
**Параметры**: request, pk, *args, **kwargs
**Возвращает**: HttpResponseRedirect

**Логика**:
1. Получает случай по pk
2. Проверяет, что случай не активен
3. Вызывает encounter.reopen_encounter()
4. Добавляет сообщения пользователю
5. Перенаправляет к деталям случая

## Формы (Forms)

### EncounterForm

#### `clean()`
**Назначение**: Валидация формы создания (наследуется от ModelForm)
**Параметры**: Нет
**Возвращает**: dict - Очищенные данные

### EncounterUpdateForm

#### `__init__(*args, **kwargs)`
**Назначение**: Инициализация формы с настройкой полей
**Параметры**: *args, **kwargs
**Возвращает**: Нет

**Логика**:
- Настраивает поле transfer_to_department
- Видимость поля управляется JavaScript в шаблоне

#### `clean()`
**Назначение**: Валидация логики переводов
**Параметры**: Нет
**Возвращает**: dict - Очищенные данные

**Логика**:
- Проверяет соответствие исхода и отделения перевода
- Добавляет ошибки в форму при несоответствии

**Примеры валидации**:
```python
# Ошибка: перевод без отделения
if outcome == 'transferred' and not transfer_to_department:
    self.add_error('transfer_to_department', "Для перевода необходимо выбрать отделение.")

# Ошибка: отделение без перевода
if outcome != 'transferred' and transfer_to_department:
    self.add_error('transfer_to_department', "Отделение для перевода может быть выбрано только при исходе 'Переведён'.")
```

### EncounterCloseForm

#### `clean()`
**Назначение**: Валидация формы закрытия с проверкой документов
**Параметры**: Нет
**Возвращает**: dict - Очищенные данные

**Логика**:
1. Валидирует логику переводов (как в EncounterUpdateForm)
2. Проверяет наличие документов у случая
3. Вызывает ValidationError если нет документов

**Исключения**:
- `ValidationError` - если нет прикрепленных документов

## Админ-панель (Admin)

### EncounterAdmin

#### `archive_selected(request, queryset)`
**Назначение**: Массовое архивирование выбранных случаев
**Параметры**: request, queryset
**Возвращает**: Нет

**Логика**:
- Вызывает archive() для каждого выбранного случая
- Добавляет сообщение пользователю

#### `unarchive_selected(request, queryset)`
**Назначение**: Массовое восстановление выбранных случаев из архива
**Параметры**: request, queryset
**Возвращает**: Нет

**Логика**:
- Сбрасывает флаги архивирования для каждого случая
- Добавляет сообщение пользователю

#### `get_queryset(request)`
**Назначение**: Получение QuerySet включая архивированные записи
**Параметры**: request
**Возвращает**: QuerySet - все записи (включая архивированные)

**Логика**:
- Использует all_objects вместо objects для включения архивированных

## Примеры комплексного использования

### Полный жизненный цикл случая обращения:

```python
# 1. Создание случая
encounter = Encounter.objects.create(
    patient=patient,
    doctor=user,
    date_start=timezone.now()
)

# 2. Добавление документов
document = ClinicalDocument.objects.create(
    content_type=ContentType.objects.get_for_model(encounter),
    object_id=encounter.id,
    document_type=document_type,
    data={'symptoms': 'Головная боль', 'diagnosis': 'Мигрень'}
)

# 3. Закрытие с переводом
if encounter.close_encounter('transferred', cardiology_department):
    # Автоматически создается PatientDepartmentStatus
    print("Случай закрыт и пациент переведен")

# 4. Возврат в активное состояние
if encounter.reopen_encounter():
    # Автоматически отменяется перевод
    print("Случай возвращен в активное состояние")

# 5. Архивирование
encounter.archive()
```

### Работа с переводами:

```python
# Создание перевода
PatientDepartmentStatus.objects.create(
    patient=encounter.patient,
    department=cardiology_department,
    status='pending',
    source_encounter=encounter
)

# Отмена перевода
patient_dept_status = PatientDepartmentStatus.objects.filter(
    patient=encounter.patient,
    department=cardiology_department,
    source_encounter=encounter
).first()

if patient_dept_status:
    patient_dept_status.cancel_transfer()
```

### Валидация данных:

```python
# Проверка активности
if encounter.is_active:
    print("Можно добавлять документы")
else:
    print("Случай закрыт")

# Проверка документов
if encounter.documents.exists():
    print("Есть документы")
else:
    print("Нет документов")

# Проверка перевода
if encounter.outcome == 'transferred':
    print(f"Переведен в {encounter.transfer_to_department.name}")
``` 