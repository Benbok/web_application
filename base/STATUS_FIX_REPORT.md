# Отчет об исправлении проблемы с автоматической установкой статуса

## Проблема
При создании записи в `examination_management` с добавлением инструментального исследования, статус автоматически становился "выполненным", при этом запись не появлялась ни в `instrumental_procedures`, ни в `clinical_scheduling`.

## Диагностика
Проблема была выявлена в следующих местах:

1. **Сигналы в `document_signatures/signals.py`**:
   - При создании `InstrumentalProcedureResult` автоматически создавались подписи
   - Подписи могли сразу устанавливать статус как завершенный

2. **Сигналы в `examination_management/signals.py`**:
   - Статус изменялся при создании результата, а не при заполнении данных
   - Отсутствовала проверка на `created` параметр

## Исправления

### 1. Изменение логики создания подписей
**Файл**: `base/document_signatures/signals.py`

**Было**:
```python
@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def create_signatures_for_instrumental_result(sender, instance, created, **kwargs):
    if created:  # Подписи создавались сразу при создании
        SignatureService.create_signatures_for_document(instance, workflow_type)
```

**Стало**:
```python
@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def create_signatures_for_instrumental_result(sender, instance, created, **kwargs):
    if not created and instance.is_completed:  # Подписи создаются только при заполнении
        if not SignatureService.get_signatures_for_document(instance).exists():
            SignatureService.create_signatures_for_document(instance, workflow_type)
```

### 2. Изменение логики синхронизации статусов
**Файл**: `base/examination_management/signals.py`

**Было**:
```python
@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def sync_instrumental_result_completion(sender, instance, **kwargs):
    # Статус изменялся при любом сохранении
```

**Стало**:
```python
@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def sync_instrumental_result_completion(sender, instance, created, **kwargs):
    if not created and instance.examination_plan:  # Только при изменении, не при создании
        if examination and instance.is_completed:
            # Статус изменяется только когда данные заполнены
```

## Результат исправления

### ✅ Что исправлено:
1. **Статус больше не устанавливается автоматически как "выполненный"** при создании записи
2. **Подписи создаются только когда результат действительно заполнен** (`is_completed=True`)
3. **Синхронизация статусов происходит только при заполнении данных**, а не при создании
4. **Записи корректно появляются в списках** `instrumental_procedures` и `clinical_scheduling`

### 🔄 Новый поток работы:
1. Создание записи в `examination_management` → статус `active`
2. Автоматическое создание результата в `instrumental_procedures` → `is_completed=False`
3. Заполнение данных врачом → `is_completed=True`
4. Автоматическое создание подписей
5. Изменение статуса на `completed` только после заполнения

### 📊 Результаты тестирования:
- **Тест 1**: Создание через сервис интеграции ✅
- **Тест 2**: Прямое создание модели ✅
- **Статус при создании**: `active` ✅
- **Статус после заполнения**: `completed` ✅
- **Подписи при создании**: 0 ✅
- **Подписи после заполнения**: создаются корректно ✅

## Файлы, измененные для исправления

1. `base/document_signatures/signals.py` - логика создания подписей
2. `base/examination_management/signals.py` - логика синхронизации статусов

## Рекомендации

1. **Тестирование**: Все исправления протестированы и работают корректно
2. **Мониторинг**: Следить за логированием ошибок в сигналах
3. **Документация**: Обновить документацию для пользователей о новом потоке работы

## Заключение
Проблема с автоматической установкой статуса "выполнено" полностью решена. Теперь система работает корректно:
- Статус устанавливается как "выполненный" только после реального заполнения данных
- Подписи создаются в нужный момент
- Записи корректно отображаются во всех связанных приложениях 