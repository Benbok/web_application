# Цветовое выделение и скрытие отмененных назначений в Clinical Scheduling

**Дата:** 04.09.2025  
**Статус:** ✅ Реализовано  
**Приоритет:** 🔵 Средний  

## Обзор изменений

В системе `clinical_scheduling` были реализованы два ключевых улучшения:

1. **Цветовое выделение назначений** по типам (examination_management vs treatment_management)
2. **Скрытие отмененных назначений** из всех списков и расписаний

## 1. Цветовое выделение назначений по типам

### Цель
Визуально различать назначения, которые приходят из разных источников:
- **examination_management** (лабораторные и инструментальные исследования)
- **treatment_management** (лекарства и рекомендации)

### Реализация

#### Обновленные шаблоны

##### `today_schedule.html`
```html
{% for appointment in schedules %}
{% with assignment_info=appointment.get_assignment_info %}
<tr class="appointment-row 
    {% if assignment_info.type == 'treatment' %}table-primary
    {% elif assignment_info.type == 'lab_test' %}table-info
    {% elif assignment_info.type == 'procedure' %}table-warning
    {% else %}table-secondary{% endif %}" 
    data-status="{{ appointment.execution_status }}">
    
    <!-- Иконки по типу назначения -->
    <td>
        <div class="d-flex align-items-center">
            {% if assignment_info.type == 'treatment' %}
                <i class="fas fa-pills me-2 text-primary"></i>
            {% elif assignment_info.type == 'lab_test' %}
                <i class="fas fa-flask me-2 text-info"></i>
            {% elif assignment_info.type == 'procedure' %}
                <i class="fas fa-stethoscope me-2 text-warning"></i>
            {% else %}
                <i class="fas fa-stethoscope me-2 text-secondary"></i>
            {% endif %}
            <div>
                <a href="{% url 'clinical_scheduling:appointment_detail' appointment.pk %}" class="text-decoration-none">
                    {{ assignment_info.name|default:"Назначение" }}
                </a>
            </div>
        </div>
    </td>
</tr>
{% endwith %}
{% endfor %}
```

##### `dashboard.html`
```html
{% for appointment in appointments %}
{% with assignment_info=appointment.get_assignment_info %}
<tr class="appointment-row 
    {% if assignment_info.type == 'treatment' %}table-primary
    {% elif assignment_info.type == 'lab_test' %}table-info
    {% elif assignment_info.type == 'procedure' %}table-warning
    {% else %}table-secondary{% endif %}"
    data-status="...">
    
    <td>
        <div class="d-flex align-items-center">
            {% if assignment_info.type == 'treatment' %}
                <i class="fas fa-pills me-2 text-primary"></i>
            {% elif assignment_info.type == 'lab_test' %}
                <i class="fas fa-flask me-2 text-info"></i>
            {% elif assignment_info.type == 'procedure' %}
                <i class="fas fa-stethoscope me-2 text-warning"></i>
            {% else %}
                <i class="fas fa-stethoscope me-2 text-secondary"></i>
            {% endif %}
            <a href="{% url 'clinical_scheduling:appointment_detail' appointment.pk %}" 
               class="text-decoration-none fw-semibold">
                {{ assignment_info.name }}
            </a>
        </div>
    </td>
</tr>
{% endwith %}
{% endfor %}
```

#### CSS стили для цветового выделения
```css
/* Цветовое выделение по типу назначения */
.table-primary {
    background-color: rgba(13, 110, 253, 0.1) !important;
}

.table-info {
    background-color: rgba(13, 202, 240, 0.1) !important;
}

.table-warning {
    background-color: rgba(255, 193, 7, 0.1) !important;
}

.table-secondary {
    background-color: rgba(108, 117, 125, 0.1) !important;
}
```

### Цветовая схема

| Тип назначения | Цвет фона | Иконка | Описание |
|----------------|-----------|--------|----------|
| **treatment** | Синий (primary) | 💊 `fa-pills` | Лекарства и рекомендации |
| **lab_test** | Голубой (info) | 🧪 `fa-flask` | Лабораторные исследования |
| **procedure** | Желтый (warning) | 🩺 `fa-stethoscope` | Инструментальные процедуры |
| **unknown** | Серый (secondary) | 🩺 `fa-stethoscope` | Неизвестный тип |

### Логика определения типа
Тип назначения определяется методом `get_assignment_info()` в модели `ScheduledAppointment`:

```python
def get_assignment_info(self):
    """Получает информацию о связанном назначении"""
    assignment = self.assignment
    
    if hasattr(assignment, 'treatment_name'):
        return {'type': 'treatment', 'name': assignment.treatment_name}
    elif hasattr(assignment, 'lab_test'):
        return {'type': 'lab_test', 'name': assignment.lab_test.name}
    elif hasattr(assignment, 'instrumental_procedure'):
        return {'type': 'procedure', 'name': assignment.instrumental_procedure.name}
    else:
        return {'type': 'unknown', 'name': str(assignment)}
```

## 2. Скрытие отмененных назначений

### Цель
Отмененные назначения (`execution_status='canceled'`) не должны отображаться в расписаниях и списках, так как они больше не актуальны для выполнения.

### Реализация

#### Обновленные сервисы (`ClinicalSchedulingService`)

##### `get_today_schedule()`
```python
@staticmethod
def get_today_schedule(patient=None, department=None, user=None):
    """Получает расписание на сегодня"""
    today = timezone.now().date()
    queryset = ScheduledAppointment.objects.filter(
        scheduled_date=today
    ).exclude(
        execution_status='canceled'  # Исключаем отмененные назначения
    ).select_related('executed_by', 'rejected_by', 'patient', 'created_department')
    
    # ... остальная логика
    return queryset.order_by('scheduled_time')
```

##### `get_overdue_appointments()`
```python
@staticmethod
def get_overdue_appointments(patient=None, department=None, user=None):
    """Получает просроченные назначения"""
    today = timezone.now().date()
    queryset = ScheduledAppointment.objects.filter(
        scheduled_date__lt=today,
        execution_status__in=['scheduled', 'partial']
    ).exclude(
        execution_status='canceled'  # Исключаем отмененные назначения
    ).select_related('executed_by', 'patient', 'created_department')
    
    # ... остальная логика
    return queryset.order_by('-scheduled_date', 'scheduled_time')
```

##### `get_patient_schedule()`
```python
@staticmethod
def get_patient_schedule(patient, start_date=None, end_date=None):
    """Получает расписание пациента за период"""
    queryset = ScheduledAppointment.objects.filter(patient=patient).exclude(
        execution_status='canceled'  # Исключаем отмененные назначения
    )
    
    # ... остальная логика
    return queryset.select_related(
        'executed_by', 'rejected_by', 'created_department'
    ).order_by('-scheduled_date', 'scheduled_time')
```

#### Обновленное представление `dashboard`

```python
def dashboard(request):
    """Главная страница планировщика"""
    # Базовый queryset
    queryset = ScheduledAppointment.objects.select_related(
        'patient', 'created_department', 'encounter', 'executed_by', 'rejected_by'
    ).exclude(
        execution_status='canceled'  # Исключаем отмененные назначения
    )
    
    # ... остальная логика
```

#### Обновленный шаблон `today_schedule.html`

Убрана логика отображения статуса `canceled`:

```html
<!-- До изменений -->
<span class="badge 
    {% if appointment.execution_status == 'completed' %}bg-success
    {% elif appointment.execution_status == 'rejected' %}bg-danger
    {% elif appointment.execution_status == 'skipped' %}bg-secondary
    {% elif appointment.execution_status == 'partial' %}bg-info
    {% elif appointment.execution_status == 'canceled' %}bg-dark
    {% else %}bg-warning{% endif %}">

<!-- После изменений -->
<span class="badge 
    {% if appointment.execution_status == 'completed' %}bg-success
    {% elif appointment.execution_status == 'rejected' %}bg-danger
    {% elif appointment.execution_status == 'skipped' %}bg-secondary
    {% elif appointment.execution_status == 'partial' %}bg-info
    {% else %}bg-warning{% endif %}">
```

## Результаты изменений

### ✅ Цветовое выделение
- **Визуальная дифференциация** назначений по источникам
- **Быстрая идентификация** типа назначения
- **Улучшенная навигация** для медперсонала
- **Совместимость** со всеми существующими функциями

### ✅ Скрытие отмененных назначений
- **Чистые списки** без отмененных назначений
- **Актуальная информация** для медперсонала
- **Упрощенная работа** с расписанием
- **Автоматическая фильтрация** на уровне запросов

### 📊 Статистика изменений

| Компонент | Изменений | Статус |
|-----------|-----------|--------|
| Шаблоны | 2 файла | ✅ |
| Сервисы | 3 метода | ✅ |
| Представления | 1 файл | ✅ |
| CSS стили | 4 класса | ✅ |
| Логика фильтрации | 4 места | ✅ |

## Технические детали

### Используемые технологии
- **Django Templates** - для условного отображения
- **Bootstrap CSS** - для цветовых классов
- **Font Awesome** - для иконок
- **Django QuerySet** - для фильтрации

### Производительность
- **Оптимизированные запросы** с `exclude()` вместо фильтрации в Python
- **Минимальные изменения** в существующем коде
- **Обратная совместимость** со всеми функциями

### Безопасность
- **Безопасные шаблоны** - использование `{% with %}` для переменных
- **Валидация данных** - проверка существования объектов
- **Graceful degradation** - корректная обработка отсутствующих данных

## Тестирование

### Проверенные сценарии
1. ✅ **Отображение назначений examination_management** - голубой/желтый цвет
2. ✅ **Отображение назначений treatment_management** - синий цвет
3. ✅ **Скрытие отмененных назначений** - не отображаются в списках
4. ✅ **Корректные иконки** - соответствуют типу назначения
5. ✅ **Фильтрация работает** - отмененные записи исключены из запросов

### Команды для проверки
```bash
# Проверка корректности кода
python manage.py check

# Сбор статических файлов
python manage.py collectstatic --noinput

# Проверка миграций
python manage.py makemigrations --dry-run
```

## Следующие шаги

### Краткосрочные (1-2 недели)
- [ ] **Добавить фильтры** по типу назначения в интерфейсе
- [ ] **Создать легенду** с описанием цветов
- [ ] **Оптимизировать запросы** для больших объемов данных

### Среднесрочные (1 месяц)
- [ ] **Расширить цветовую схему** для других типов назначений
- [ ] **Добавить анимации** при смене фильтров
- [ ] **Создать дашборд** с статистикой по типам назначений

### Долгосрочные (3 месяца)
- [ ] **Интеграция с календарем** - цветовое выделение в календарном виде
- [ ] **Персонализация** - пользовательские настройки цветов
- [ ] **Экспорт данных** с сохранением цветовой информации

## Заключение

Реализованные изменения значительно улучшают пользовательский опыт в системе `clinical_scheduling`:

1. **Цветовое выделение** позволяет быстро идентифицировать тип назначения
2. **Скрытие отмененных назначений** упрощает работу с актуальными данными
3. **Минимальные изменения** обеспечивают стабильность системы
4. **Обратная совместимость** гарантирует работу всех существующих функций

Система теперь предоставляет более интуитивный и эффективный интерфейс для управления медицинскими назначениями.

---

**Документ подготовлен:** Системный архитектор  
**Дата:** 04.09.2025  
**Статус:** ✅ Изменения реализованы и протестированы
