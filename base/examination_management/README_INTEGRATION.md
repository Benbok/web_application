# Интеграция examination_management с другими приложениями

## Обзор

Приложение `examination_management` интегрировано с несколькими другими приложениями для обеспечения полного цикла управления медицинскими назначениями.

## Интеграция с clinical_scheduling

### Назначения и статусы

- **ExaminationLabTest** и **ExaminationInstrumental** автоматически создают записи в `clinical_scheduling.ScheduledAppointment`
- Статусы синхронизируются между приложениями через `ExaminationStatusService`
- Поддерживаются все статусы: `active`, `completed`, `paused`, `rejected`, `cancelled`

### Сервис управления статусами

```python
from examination_management.services import ExaminationStatusService

# Получение статуса назначения
status = ExaminationStatusService.get_assignment_status(examination_item)

# Обновление статуса
ExaminationStatusService.update_assignment_status(
    examination_item, 'completed', user, 'Завершено'
)

# Создание расписания
schedules = ExaminationStatusService.create_schedule_for_assignment(
    examination_item, user, start_date, first_time, times_per_day, duration_days
)
```

## Интеграция с instrumental_procedures

### Автоматическое создание результатов

При создании `ExaminationInstrumental` автоматически создается запись `InstrumentalProcedureResult`:

- **Пациент** - берется из плана обследования
- **Тип исследования** - связывается с `InstrumentalProcedureDefinition`
- **План обследования** - ссылка на `ExaminationPlan`
- **Автор** - пользователь, создавший назначение
- **Данные** - пустой JSON для заполнения врачом/лаборантом

### Доступ к результатам

В шаблоне `plan_detail.html` добавлена кнопка "Заполнить результат", которая ведет на:
```
{% url 'instrumental_procedures:result_update' instrumental.pk %}
```

## Интеграция с lab_tests

### Автоматическое создание результатов

При создании `ExaminationLabTest` автоматически создается запись `LabTestResult`:

- **Пациент** - берется из плана обследования  
- **Тип исследования** - связывается с `LabTestDefinition`
- **План обследования** - ссылка на `ExaminationPlan`
- **Автор** - пользователь, создавший назначение
- **Данные** - пустой JSON для заполнения врачом/лаборантом

### Доступ к результатам

В шаблоне `plan_detail.html` добавлена кнопка "Заполнить результат", которая ведет на:
```
{% url 'lab_tests:result_update' lab_test.pk %}
```

## Сервис интеграции

### ExaminationIntegrationService

```python
from examination_management.services import ExaminationIntegrationService

# Создание результата инструментального исследования
result = ExaminationIntegrationService.create_instrumental_procedure_result(
    examination_instrumental, user
)

# Создание результата лабораторного исследования  
result = ExaminationIntegrationService.create_lab_test_result(
    examination_lab_test, user
)
```

## Сигналы Django

### Автоматическое создание результатов

```python
@receiver(post_save, sender=ExaminationLabTest)
def create_lab_test_result_on_save(sender, instance, created, **kwargs):
    """Автоматически создает LabTestResult при создании ExaminationLabTest"""
    if created:
        # Создание результата через сервис интеграции
        pass

@receiver(post_save, sender=ExaminationInstrumental)  
def create_instrumental_procedure_result_on_save(sender, instance, created, **kwargs):
    """Автоматически создает InstrumentalProcedureResult при создании ExaminationInstrumental"""
    if created:
        # Создание результата через сервис интеграции
        pass
```

### Синхронизация статусов

```python
@receiver(post_save, sender=ExaminationLabTest)
def sync_examination_lab_test_status(sender, instance, created, **kwargs):
    """Синхронизирует статус с ScheduledAppointment"""
    # Обновление статусов в clinical_scheduling
    pass
```

## URL-паттерны

### examination_management

- `lab_test_create/<int:plan_pk>/` - создание лабораторного исследования
- `instrumental_create/<int:plan_pk>/` - создание инструментального исследования
- `plan_detail/<str:owner_model>/<int:owner_id>/<int:pk>/` - детали плана

### instrumental_procedures

- `results/` - список результатов
- `results/create/` - создание результата
- `results/<int:pk>/` - детали результата
- `results/<int:pk>/update/` - редактирование результата

### lab_tests

- `results/` - список результатов
- `results/create/` - создание результата  
- `results/<int:pk>/` - детали результата
- `results/<int:pk>/update/` - редактирование результата

## Шаблоны

### plan_detail.html

Основной шаблон плана обследования с:
- Списком лабораторных исследований
- Списком инструментальных исследований
- Кнопками управления статусами
- **Кнопками "Заполнить результат"** для перехода к заполнению данных

### result_list.html (instrumental_procedures)

Список результатов инструментальных исследований с:
- Поиском и фильтрацией
- Отображением в виде карточек
- Пагинацией
- Кнопками просмотра и редактирования

### result_create.html (instrumental_procedures)

Форма создания результата с:
- Выбором типа исследования
- Выбором пациента
- Установкой даты и времени

## Преимущества интеграции

1. **Автоматизация** - результаты создаются автоматически при назначении
2. **Единообразие** - все назначения и результаты в одном месте
3. **Отслеживание** - полная история назначений и результатов
4. **Удобство** - врач/лаборант сразу видит, что нужно заполнить
5. **Синхронизация** - статусы обновляются автоматически

## Тестирование

Для тестирования интеграции используйте команду:

```bash
python manage.py test_integration
```

Эта команда проверяет:
- Создание тестовых данных
- Автоматическое создание результатов
- Работу сервиса интеграции
- Синхронизацию между приложениями 