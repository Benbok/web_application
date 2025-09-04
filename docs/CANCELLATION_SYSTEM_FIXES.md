# Исправления системы отмены назначений

## Проблемы, которые были исправлены

### 1. Проблема с импортом ContentType
**Проблема:** В методах `can_be_cancelled()` не был импортирован `ContentType`, что приводило к ошибкам.

**Решение:** Добавлен импорт в оба метода:
```python
from django.contrib.contenttypes.models import ContentType
```

### 2. Проблема с отображением кнопок в шаблонах
**Проблема:** Кнопки все еще назывались "Удалить" вместо "Отменить".

**Решение:** Обновлены шаблоны:
- `examination_management/templates/examination_management/plan_detail.html`
- `treatment_management/templates/treatment_management/plan_detail.html`

### 3. Проблема с отображением отмененных назначений
**Проблема:** Отмененные назначения не отображались в планах.

**Решение:** Добавлено отображение отмененных назначений:
- Добавлен блок для отмененных исследований в шаблонах
- Добавлено отображение информации об отмене (время, пользователь, причина)
- Добавлены соответствующие бейджи и стили

### Исправление отображения статуса отмены в интерфейсе lab_tests

#### Проблема
При отмене назначения в `examination_management` статус в `lab_tests` не отображался как "Отменено" в пользовательском интерфейсе. Вместо этого отображался статус "Ожидает заполнения" на основе поля `is_completed`.

#### Решение
Обновлен шаблон `lab_tests/result_list.html` для правильного отображения статуса отмены:

```html
<!-- До исправления -->
{% if result.is_completed %}
    <span class="badge bg-success">Заполнено</span>
{% else %}
    <span class="badge bg-warning">Ожидает заполнения</span>
{% endif %}

<!-- После исправления -->
{% if result.status == 'active' %}
    {% if result.is_completed %}
        <span class="badge bg-success">Заполнено</span>
    {% else %}
        <span class="badge bg-warning">Ожидает заполнения</span>
    {% endif %}
{% elif result.status == 'cancelled' %}
    <span class="badge bg-secondary">Отменено</span>
{% elif result.status == 'completed' %}
    <span class="badge bg-success">Завершено</span>
{% elif result.status == 'paused' %}
    <span class="badge bg-warning">Приостановлено</span>
{% else %}
    <span class="badge bg-light text-dark">{{ result.get_status_display }}</span>
{% endif %}
```

#### Обновление кнопок действий
Добавлена проверка статуса отмены для кнопок действий:

```html
{% if result.status == 'cancelled' %}
    <span class="btn btn-outline-secondary disabled">
        <i class="fas fa-ban me-1"></i>Отменено
    </span>
{% elif result.is_completed %}
    <a href="{% url 'lab_tests:result_detail' result.pk %}" class="btn btn-outline-info">
        <i class="fas fa-eye me-1"></i>Просмотреть
    </a>
    <a href="{% url 'lab_tests:result_update' result.pk %}" class="btn btn-outline-warning">
        <i class="fas fa-edit me-1"></i>Редактировать
    </a>
{% else %}
    <a href="{% url 'lab_tests:result_update' result.pk %}" class="btn btn-primary">
        <i class="fas fa-plus me-1"></i>Добавить данные
    </a>
{% endif %}
```

#### Обновление фильтрации
Добавлена фильтрация по статусу в представление `LabTestResultListView`:

```python
def get_queryset(self):
    queryset = super().get_queryset()
    query = self.request.GET.get('q')
    status = self.request.GET.get('status')
    
    if query:
        # Поиск по пациенту или исследованию
        query = query.strip().lower()
        queryset = queryset.filter(
            Q(patient__first_name__icontains=query) |
            Q(patient__last_name__icontains=query) |
            Q(patient__middle_name__icontains=query) |
            Q(procedure_definition__name__icontains=query)
        )
    
    # Фильтрация по статусу
    if status:
        if status == 'completed':
            queryset = queryset.filter(is_completed=True)
        elif status == 'active':
            queryset = queryset.filter(status='active')
        elif status == 'cancelled':
            queryset = queryset.filter(status='cancelled')
    
    return queryset
```

### Тестирование исправления отображения статуса

#### Тест отображения отмененной записи
```python
# Проверка отмененной записи
result = LabTestResult.objects.get(id=49)
print('LabTestResult для проверки UI:')
print('ID:', result.id)  # 49
print('Status:', result.status)  # 'cancelled' ✅
print('Is completed:', result.is_completed)  # False ✅
print('Cancelled at:', result.cancelled_at)  # 2025-09-04 13:57:14 ✅
```

#### Результат исправления
- ✅ **Отмененные записи отображаются** с бейджем "Отменено"
- ✅ **Кнопки действий отключены** для отмененных записей
- ✅ **Фильтрация по статусу** работает корректно
- ✅ **Синхронизация отмены** между приложениями работает

## Исправленные файлы

### Модели
- `base/examination_management/models.py` - добавлен импорт ContentType
- `base/treatment_management/models.py` - добавлен импорт ContentType

### Шаблоны
- `base/examination_management/templates/examination_management/plan_detail.html`
  - Обновлены кнопки с "Удалить" на "Отменить"
  - Добавлено отображение отмененных исследований
  - Добавлена информация об отмене

- `base/treatment_management/templates/treatment_management/plan_detail.html`
  - Обновлены кнопки с "Удалить" на "Отменить"
  - Добавлено отображение отмененных назначений

- `base/examination_management/templates/examination_management/lab_test_confirm_delete.html`
- `base/examination_management/templates/examination_management/instrumental_confirm_delete.html`
- `base/treatment_management/templates/treatment_management/medication_confirm_delete.html`
- `base/treatment_management/templates/treatment_management/recommendation_confirm_delete.html`
  - Обновлены диалоги подтверждения отмены
  - Добавлена проверка возможности отмены

### Views
- `base/examination_management/views.py` - обновлены DeleteView для отмены
- `base/treatment_management/views.py` - обновлены DeleteView для отмены

### Решение
Созданы отдельные представления для отмены без физического удаления, использующие существующие формы подтверждения:

#### 1. Новые представления отмены (DetailView)
```python
class ExaminationLabTestCancelView(LoginRequiredMixin, DetailView):
    """
    Отмена лабораторного исследования без физического удаления
    """
    model = ExaminationLabTest
    template_name = 'examination_management/lab_test_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        
        # Получаем владельца и пациента
        owner = self.object.examination_plan.get_owner()
        if owner:
            context['owner'] = owner
            context['patient'] = self.get_patient_from_owner(owner)
            context['owner_model'] = owner._meta.model_name
            context['owner_id'] = owner.id
            
            # Если владелец - это Encounter, добавляем его в контекст
            if isinstance(owner, Encounter):
                context['encounter'] = owner
        else:
            context['encounter'] = None
            context['patient'] = None
        
        context['title'] = _('Отменить лабораторное исследование')
        
        # Проверяем возможность отмены
        can_cancel, error_message = self.object.can_be_cancelled()
        context['can_be_cancelled'] = can_cancel
        context['warning_message'] = error_message
        
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Обрабатываем POST-запрос для отмены назначения
        """
        self.object = self.get_object()
        
        # Проверяем возможность отмены
        can_cancel, error_message = self.object.can_be_cancelled()
        if not can_cancel:
            messages.error(request, error_message)
            return redirect(self.get_success_url())
        
        # Отменяем назначение
        try:
            self.object.cancel(
                reason="Отменено через веб-интерфейс",
                cancelled_by=request.user
            )
            messages.success(request, _('Лабораторное исследование успешно отменено'))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, _('Ошибка при отмене исследования: {}').format(str(e)))
        
        return redirect(self.get_success_url())
```

**Ключевое исправление:** Использование `DetailView` вместо `DeleteView` и обработка `POST`-запроса вместо `delete()` предотвращает физическое удаление объекта Django.

## Логика работы системы отмены

### 1. Проверка возможности отмены
```python
def can_be_cancelled(self):
    """
    Проверяет, можно ли отменить назначение
    Нельзя отменить, если есть подписанное заключение
    """
    # Проверяет наличие подписанных заключений
    # Возвращает (bool, str) - (можно_отменить, сообщение_об_ошибке)
```

### 2. Отмена назначения
```python
def cancel(self, reason="", cancelled_by=None):
    """
    Отменяет назначение
    """
    # Устанавливает статус 'cancelled'
    # Записывает время, пользователя и причину отмены
    # Синхронизирует с clinical_scheduling
```

### 3. Отображение в шаблонах
```html
{% with can_cancel=lab_test.can_be_cancelled %}
{% if can_cancel.0 %}
    <a href="{% url 'examination_management:lab_test_delete' pk=lab_test.pk %}" 
       class="btn btn-outline-warning btn-sm">
        <i class="fas fa-ban me-1"></i> Отменить
    </a>
{% else %}
    <span class="btn btn-outline-secondary btn-sm disabled" 
          title="{{ can_cancel.1 }}">
        <i class="fas fa-ban me-1"></i> Отменить
    </span>
{% endif %}
{% endwith %}
```

## Статусы назначений

1. **active** - Активно (зеленый бейдж)
2. **cancelled** - Отменено (серый бейдж)
3. **completed** - Завершено (зеленый бейдж)
4. **paused** - Приостановлено (желтый бейдж)
5. **rejected** - Забраковано (красный бейдж)

## Интеграция с clinical_scheduling

При отмене назначения автоматически обновляется статус в `ScheduledAppointment`:
- `status = 'cancelled'` → `execution_status = 'canceled'`

## Тестирование

Система была протестирована:
1. ✅ Метод `can_be_cancelled()` возвращает кортеж `(True, None)` для активных назначений
2. ✅ Метод `cancel()` правильно устанавливает статус 'cancelled'
3. ✅ Отмененные назначения отображаются в планах
4. ✅ Кнопки правильно называются "Отменить"
5. ✅ Проверка подписанных заключений работает

## Результат

Теперь система отмены назначений работает корректно:
- Назначения отменяются вместо удаления
- Отмененные назначения остаются видимыми в планах
- Кнопки правильно называются "Отменить"
- Проверка возможности отмены работает
- Интеграция с clinical_scheduling работает

## Восстановленный функционал автоматического создания записей и синхронизации

### Автоматическое создание записей при создании назначений

При создании назначения в `examination_management` автоматически создается соответствующая запись в `lab_tests` или `instrumental_procedures` для заполнения лаборантом.

#### Сигналы создания записей

```python
@receiver(post_save, sender=ExaminationLabTest)
def create_lab_test_result(sender, instance, created, **kwargs):
    """
    Создает запись результата лабораторного исследования при создании назначения
    """
    if created:
        try:
            from lab_tests.models import LabTestResult
            
            # Проверяем, есть ли уже результат для этого назначения
            existing_result = LabTestResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.lab_test
            ).first()
            
            if not existing_result:
                # Создаем новый результат
                LabTestResult.objects.create(
                    patient=instance.examination_plan.get_patient(),
                    examination_plan=instance.examination_plan,
                    procedure_definition=instance.lab_test,
                    author=instance.examination_plan.get_owner().get_user() if hasattr(instance.examination_plan.get_owner(), 'get_user') else None
                )
                print(f"Создан LabTestResult для ExaminationLabTest {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при создании LabTestResult: {e}")


@receiver(post_save, sender=ExaminationInstrumental)
def create_instrumental_procedure_result(sender, instance, created, **kwargs):
    """
    Создает запись результата инструментального исследования при создании назначения
    """
    if created:
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            
            # Проверяем, есть ли уже результат для этого назначения
            existing_result = InstrumentalProcedureResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.instrumental_procedure
            ).first()
            
            if not existing_result:
                # Создаем новый результат
                InstrumentalProcedureResult.objects.create(
                    patient=instance.examination_plan.get_patient(),
                    examination_plan=instance.examination_plan,
                    procedure_definition=instance.instrumental_procedure,
                    author=instance.examination_plan.get_owner().get_user() if hasattr(instance.examination_plan.get_owner(), 'get_user') else None
                )
                print(f"Создан InstrumentalProcedureResult для ExaminationInstrumental {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при создании InstrumentalProcedureResult: {e}")
```

### Синхронизация отмены между приложениями

При отмене назначения в `examination_management` автоматически отменяется соответствующая запись в `lab_tests` или `instrumental_procedures`.

#### Сигналы синхронизации отмены

```python
@receiver(post_save, sender=ExaminationLabTest)
def sync_lab_test_cancellation(sender, instance, created, **kwargs):
    """
    Синхронизирует отмену лабораторного исследования с lab_tests
    
    Когда ExaminationLabTest отменяется, автоматически отменяется
    соответствующий LabTestResult в lab_tests
    """
    if created:
        # Новое исследование - ничего не синхронизируем
        return
    
    if instance.status == 'cancelled':
        try:
            from lab_tests.models import LabTestResult
            
            # Находим соответствующий результат лабораторного исследования
            lab_test_result = LabTestResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.lab_test
            ).first()
            
            if lab_test_result and lab_test_result.status != 'cancelled':
                # Отменяем результат исследования
                lab_test_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {instance.cancellation_reason}",
                    cancelled_by=instance.cancelled_by
                )
                print(f"Отменен LabTestResult {lab_test_result.pk} для ExaminationLabTest {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при синхронизации отмены с lab_tests: {e}")


@receiver(post_save, sender=ExaminationInstrumental)
def sync_instrumental_cancellation(sender, instance, created, **kwargs):
    """
    Синхронизирует отмену инструментального исследования с instrumental_procedures
    
    Когда ExaminationInstrumental отменяется, автоматически отменяется
    соответствующий InstrumentalProcedureResult в instrumental_procedures
    """
    if created:
        # Новое исследование - ничего не синхронизируем
        return
    
    if instance.status == 'cancelled':
        try:
            from instrumental_procedures.models import InstrumentalProcedureResult
            
            # Находим соответствующий результат инструментального исследования
            instrumental_result = InstrumentalProcedureResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.instrumental_procedure
            ).first()
            
            if instrumental_result and instrumental_result.status != 'cancelled':
                # Отменяем результат исследования
                instrumental_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {instance.cancellation_reason}",
                    cancelled_by=instance.cancelled_by
                )
                print(f"Отменен InstrumentalProcedureResult {instrumental_result.pk} для ExaminationInstrumental {instance.pk}")
                
        except Exception as e:
            print(f"Ошибка при синхронизации отмены с instrumental_procedures: {e}")
```

### Тестирование восстановленного функционала

#### Тест создания лабораторного исследования
```python
# Создание назначения в examination_management
exam = ExaminationLabTest.objects.create(
    examination_plan=plan,
    lab_test=lab_test,
    instructions='Тест автоматического создания записи в lab_tests - новый тип'
)
# Результат: "Создан LabTestResult для ExaminationLabTest 96"

# Проверка создания записи в lab_tests
result = LabTestResult.objects.filter(
    examination_plan=exam.examination_plan,
    procedure_definition=exam.lab_test
).first()
print('LabTestResult ID:', result.id)  # 47 ✅
```

#### Тест синхронизации отмены лабораторного исследования
```python
# Отмена назначения в examination_management
exam.cancel(reason='Тест синхронизации отмены', cancelled_by=user)
# Результат: "Отменен LabTestResult 47 для ExaminationLabTest 96"

# Проверка отмены записи в lab_tests
result.refresh_from_db()
print('LabTestResult Status:', result.status)  # 'cancelled' ✅
print('LabTestResult Cancelled at:', result.cancelled_at)  # 2025-09-04 13:54:13 ✅
```

#### Тест создания инструментального исследования
```python
# Создание назначения в examination_management
exam = ExaminationInstrumental.objects.create(
    examination_plan=plan,
    instrumental_procedure=instrumental,
    instructions='Тест автоматического создания записи в instrumental_procedures'
)
# Результат: "Создан InstrumentalProcedureResult для ExaminationInstrumental 49"

# Проверка создания записи в instrumental_procedures
result = InstrumentalProcedureResult.objects.filter(
    examination_plan=exam.examination_plan,
    procedure_definition=exam.instrumental_procedure
).first()
print('InstrumentalProcedureResult ID:', result.id)  # 51 ✅
```

#### Тест синхронизации отмены инструментального исследования
```python
# Отмена назначения в examination_management
exam.cancel(reason='Тест синхронизации отмены инструментального', cancelled_by=user)
# Результат: "Отменен InstrumentalProcedureResult 51 для ExaminationInstrumental 49"

# Проверка отмены записи в instrumental_procedures
result.refresh_from_db()
print('InstrumentalProcedureResult Status:', result.status)  # 'cancelled' ✅
print('InstrumentalProcedureResult Cancelled at:', result.cancelled_at)  # 2025-09-04 13:54:36 ✅
```

### Результаты восстановленного функционала

#### ✅ Автоматическое создание записей
- **При создании назначения** в `examination_management` автоматически создается запись в `lab_tests`/`instrumental_procedures`
- **Лаборант может заполнить данные** в соответствующем приложении
- **Врач видит результаты** в плане обследования

#### ✅ Синхронизация отмены
- **При отмене назначения** в `examination_management` автоматически отменяется запись в `lab_tests`/`instrumental_procedures`
- **Лаборант видит отмену** в своем интерфейсе
- **Сохранение причины отмены** и пользователя, который отменил

#### ✅ Полный цикл работы
1. **Врач создает назначение** → автоматически создается запись для лаборанта
2. **Лаборант заполняет данные** → врач видит результаты в плане
3. **Врач отменяет назначение** → автоматически отменяется у лаборанта
4. **Все данные сохраняются** для аудита и истории

## Решение проблемы с физическим удалением записей при отмене
