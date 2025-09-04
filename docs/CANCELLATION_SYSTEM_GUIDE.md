# Система отмены назначений - Руководство

## Обзор

Система отмены назначений позволяет врачам отменять назначения (лекарства, исследования, рекомендации) вместо их физического удаления. Отмененные назначения остаются в системе для аудита и истории, но становятся недоступными для редактирования.

**НОВОЕ:** Полная синхронизация отмены между всеми приложениями - при отмене назначения в `examination_management` автоматически отменяются соответствующие записи в `lab_tests` и `instrumental_procedures`.

## Архитектура

### Модели с поддержкой отмены

#### ExaminationLabTest
- **Поле статуса:** `status` (active, cancelled, completed, paused)
- **Информация об отмене:** `cancelled_at`, `cancelled_by`, `cancellation_reason`
- **Метод отмены:** `cancel(reason, cancelled_by)`
- **Проверка возможности отмены:** `can_be_cancelled()`
- **Синхронизация:** `_sync_with_lab_tests()`, `_sync_with_clinical_scheduling()`

#### ExaminationInstrumental
- **Поле статуса:** `status` (active, cancelled, completed, paused)
- **Информация об отмене:** `cancelled_at`, `cancelled_by`, `cancellation_reason`
- **Метод отмены:** `cancel(reason, cancelled_by)`
- **Проверка возможности отмены:** `can_be_cancelled()`
- **Синхронизация:** `_sync_with_instrumental_procedures()`, `_sync_with_clinical_scheduling()`

#### LabTestResult (НОВОЕ)
- **Поле статуса:** `status` (active, cancelled, completed, paused)
- **Информация об отмене:** `cancelled_at`, `cancelled_by`, `cancellation_reason`
- **Метод отмены:** `cancel(reason, cancelled_by)`

#### InstrumentalProcedureResult (НОВОЕ)
- **Поле статуса:** `status` (active, cancelled, completed, paused)
- **Информация об отмене:** `cancelled_at`, `cancelled_by`, `cancellation_reason`
- **Метод отмены:** `cancel(reason, cancelled_by)`

#### TreatmentMedication
- **Поле статуса:** `status` (active, cancelled, completed, paused)
- **Информация об отмене:** `cancelled_at`, `cancelled_by`, `cancellation_reason`
- **Метод отмены:** `cancel(reason, cancelled_by)`
- **Проверка возможности отмены:** `can_be_cancelled()`

#### TreatmentRecommendation
- **Поле статуса:** `status` (active, cancelled, completed, paused)
- **Информация об отмене:** `cancelled_at`, `cancelled_by`, `cancellation_reason`
- **Метод отмены:** `cancel(reason, cancelled_by)`
- **Проверка возможности отмены:** `can_be_cancelled()`

### Статусы назначений

1. **active** - Активно
   - Назначение активно и может быть выполнено
   - Доступно для редактирования и отмены
   - Отображается в расписании

2. **cancelled** - Отменено
   - Назначение отменено врачом
   - Недоступно для редактирования
   - Отображается в истории с пометкой "Отменено"
   - Автоматически отменяет связанные события в clinical_scheduling
   - **НОВОЕ:** Автоматически отменяет соответствующие записи в lab_tests/instrumental_procedures

3. **completed** - Завершено
   - Назначение выполнено
   - Недоступно для редактирования
   - Отображается в истории с пометкой "Завершено"

4. **paused** - Приостановлено
   - Назначение временно приостановлено
   - Может быть возобновлено
   - Отображается в истории с пометкой "Приостановлено"

## Логика отмены

### Проверка возможности отмены

#### Для лабораторных исследований (ExaminationLabTest)
```python
def can_be_cancelled(self):
    """
    Проверяет, можно ли отменить назначение
    Нельзя отменить, если есть подписанное заключение
    """
    try:
        from lab_tests.models import LabTestResult
        from document_signatures.models import DocumentSignature
        
        # Проверяем, есть ли заполненный результат
        result = LabTestResult.objects.filter(
            examination_plan=self.examination_plan,
            procedure_definition=self.lab_test,
            is_completed=True
        ).first()
        
        if result:
            # Проверяем, есть ли подпись
            signature = DocumentSignature.objects.filter(
                content_type=ContentType.objects.get_for_model(LabTestResult),
                object_id=result.pk,
                is_signed=True
            ).first()
            
            if signature:
                return False, "Есть подписанное заключение. Сначала удалите заключение в разделе лабораторных исследований."
        
        return True, None
        
    except Exception:
        return True, None
```

#### Для инструментальных исследований (ExaminationInstrumental)
Аналогичная логика, но проверяет `InstrumentalProcedureResult` и соответствующие подписи.

#### Для лекарств и рекомендаций
```python
def can_be_cancelled(self):
    """
    Проверяет, можно ли отменить назначение
    Для лекарств и рекомендаций пока нет системы подписей
    """
    return True, None
```

### Процесс отмены

1. **Проверка возможности отмены**
   - Вызывается `can_be_cancelled()`
   - Если возвращает `False`, отмена блокируется

2. **Обновление статуса**
   - Устанавливается `status = 'cancelled'`
   - Записывается `cancelled_at = timezone.now()`
   - Записывается `cancelled_by = user`
   - Записывается `cancellation_reason = reason`

3. **Синхронизация с clinical_scheduling**
   - Автоматически обновляется `execution_status = 'canceled'` в `ScheduledAppointment`
   - Все связанные события помечаются как отмененные

4. **НОВОЕ: Синхронизация с lab_tests/instrumental_procedures**
   - Автоматически отменяется соответствующий `LabTestResult` или `InstrumentalProcedureResult`
   - Статус меняется на 'cancelled' с сохранением причины отмены

## Полная синхронизация отмены

### Автоматическое создание записей результатов
При создании назначения в `examination_management` автоматически создается соответствующая запись в `lab_tests` или `instrumental_procedures`:

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
                
        except Exception as e:
            print(f"Ошибка при создании LabTestResult: {e}")
```

### Автоматическая синхронизация отмены
При отмене назначения в `examination_management` автоматически отменяется соответствующая запись в `lab_tests` или `instrumental_procedures`:

```python
@receiver(post_save, sender=ExaminationLabTest)
def sync_lab_test_cancellation(sender, instance, created, **kwargs):
    """
    Синхронизирует отмену лабораторного исследования с lab_tests
    
    Когда ExaminationLabTest отменяется, автоматически отменяется
    соответствующий LabTestResult в lab_tests
    """
    if created:
        return
    
    if instance.status == 'cancelled':
        try:
            from lab_tests.models import LabTestResult
            
            lab_test_result = LabTestResult.objects.filter(
                examination_plan=instance.examination_plan,
                procedure_definition=instance.lab_test
            ).first()
            
            if lab_test_result and lab_test_result.status != 'cancelled':
                lab_test_result.cancel(
                    reason=f"Отменено назначение в плане обследования: {instance.cancellation_reason}",
                    cancelled_by=instance.cancelled_by
                )
                
        except Exception as e:
            print(f"Ошибка при синхронизации отмены с lab_tests: {e}")
```

## Интерфейс

### Кнопки в списках назначений

#### Активные назначения
- **Редактировать** - иконка карандаша, синяя кнопка
- **Отменить** - иконка запрета, желтая кнопка

#### Отмененные назначения
- **Отменено** - текст с датой отмены
- Кнопки редактирования и отмены скрыты

### Диалоги подтверждения отмены

#### Структура диалога
1. **Заголовок** - "Подтверждение отмены"
2. **Информация о назначении** - название, детали
3. **Предупреждение** (если отмена невозможна)
4. **Описание процесса отмены** - что происходит при отмене
5. **Кнопки** - "Отменить назначение" и "Отмена"

#### Пример для лабораторного исследования
```html
<div class="alert alert-info">
    <h5>Информация об отмене исследования</h5>
    <p>Вы собираетесь <strong>отменить</strong> лабораторное исследование:</p>
    <ul>
        <li><strong>Название:</strong> {{ object.get_lab_test_name }}</li>
        <li><strong>Примечания:</strong> {{ object.instructions }}</li>
    </ul>
</div>

<div class="alert alert-success">
    <h6>Что происходит при отмене:</h6>
    <ul>
        <li>Исследование помечается как "Отменено"</li>
        <li>Сохраняется полная история назначения</li>
        <li>Автоматически отменяются все запланированные события</li>
        <li>Запись остается в базе данных для аудита</li>
        <li><strong>НОВОЕ:</strong> Автоматически отменяется соответствующая запись в лабораторных исследованиях</li>
    </ul>
</div>
```

### Отображение в истории пациента

#### Активные назначения
- Обычные карточки с кнопками редактирования и отмены
- Статус: "Активно" (зеленый)

#### Отмененные назначения
- Карточки с серой рамкой и светлым фоном
- Бейдж "Отменено" рядом с названием
- Статус: "Отменено" (серый)
- Причина отмены (если указана)
- Дата и время отмены

## API для разработчиков

### Отмена назначения
```python
# Отмена лабораторного исследования
lab_test = ExaminationLabTest.objects.get(pk=1)
try:
    lab_test.cancel(
        reason="Пациент отказался от исследования",
        cancelled_by=request.user
    )
    messages.success(request, "Исследование отменено")
except ValidationError as e:
    messages.error(request, str(e))
```

### Проверка возможности отмены
```python
# Проверка перед отменой
can_cancel, error_message = lab_test.can_be_cancelled()
if not can_cancel:
    messages.error(request, error_message)
else:
    # Выполняем отмену
    lab_test.cancel(reason="...", cancelled_by=user)
```

### Получение отмененных назначений
```python
# Все отмененные лабораторные исследования
cancelled_lab_tests = ExaminationLabTest.objects.filter(status='cancelled')

# Отмененные назначения конкретного плана
plan = ExaminationPlan.objects.get(pk=1)
cancelled_medications = plan.medications.filter(status='cancelled')

# НОВОЕ: Отмененные результаты лабораторных исследований
cancelled_results = LabTestResult.objects.filter(status='cancelled')
```

## Интеграция с clinical_scheduling

### Автоматическая синхронизация
При изменении статуса назначения автоматически обновляется `execution_status` в `ScheduledAppointment`:

- `status = 'cancelled'` → `execution_status = 'canceled'`
- `status = 'completed'` → `execution_status = 'completed'`
- `status = 'paused'` → `execution_status = 'skipped'`
- `status = 'active'` → `execution_status = 'scheduled'`

### Метод синхронизации
```python
def _sync_with_clinical_scheduling(self):
    """
    Синхронизирует статус с clinical_scheduling
    """
    try:
        from clinical_scheduling.models import ScheduledAppointment
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(self)
        appointments = ScheduledAppointment.objects.filter(
            content_type=content_type,
            object_id=self.pk
        )
        
        for appointment in appointments:
            if self.status == 'cancelled':
                appointment.execution_status = 'canceled'
            elif self.status == 'completed':
                appointment.execution_status = 'completed'
            elif self.status == 'paused':
                appointment.execution_status = 'skipped'
            elif self.status == 'active':
                appointment.execution_status = 'scheduled'
            
            appointment.save(update_fields=['execution_status'])
            
    except Exception as e:
        print(f"Ошибка синхронизации с clinical_scheduling: {e}")
```

## Безопасность

### Проверки перед отменой
1. **Подписанные заключения** - нельзя отменить исследование с подписанным заключением
2. **Права доступа** - только авторизованные пользователи могут отменять назначения
3. **Валидация данных** - проверка корректности причины отмены

### Аудит
1. **Логирование** - все операции отмены записываются в `cancelled_at`, `cancelled_by`
2. **История** - отмененные назначения остаются в системе для аудита
3. **Причины** - обязательное указание причины отмены
4. **Синхронизация** - все изменения синхронизируются между приложениями

## Миграции

### Добавленные поля
```python
# Статус назначения
status = models.CharField(
    _('Статус'),
    max_length=20,
    choices=STATUS_CHOICES,
    default='active'
)

# Информация об отмене
cancelled_at = models.DateTimeField(_('Отменено'), null=True, blank=True)
cancelled_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name=_('Отменено пользователем'),
    related_name='cancelled_...'
)
cancellation_reason = models.TextField(_('Причина отмены'), blank=True)
```

### Миграции
- `examination_management.0005_examinationinstrumental_cancellation_reason_and_more.py`
- `treatment_management.0009_alter_treatmentmedication_options_and_more.py`
- `lab_tests.0005_labtestresult_cancellation_reason_and_more.py` (НОВОЕ)
- `instrumental_procedures.0005_instrumentalprocedureresult_cancellation_reason_and_more.py` (НОВОЕ)

## Тестирование

### Сценарии тестирования
1. **Отмена активного назначения** - проверка успешной отмены
2. **Отмена с подписанным заключением** - проверка блокировки
3. **Отмена без прав доступа** - проверка безопасности
4. **Синхронизация с clinical_scheduling** - проверка обновления статусов
5. **НОВОЕ: Синхронизация с lab_tests** - проверка отмены результатов
6. **НОВОЕ: Синхронизация с instrumental_procedures** - проверка отмены результатов
7. **Отображение в истории** - проверка корректного отображения

### Команды для тестирования
```bash
# Запуск тестов
python manage.py test examination_management.tests
python manage.py test treatment_management.tests
python manage.py test lab_tests.tests
python manage.py test instrumental_procedures.tests

# Проверка миграций
python manage.py makemigrations --dry-run
python manage.py migrate --plan
```

## Заключение

Система отмены назначений обеспечивает:
- **Безопасность** - проверки перед отменой
- **Аудит** - полная история всех операций
- **Интеграцию** - синхронизация с clinical_scheduling
- **НОВОЕ: Полную синхронизацию** - отмена между всеми приложениями
- **Удобство** - понятный интерфейс для пользователей
- **Гибкость** - возможность расширения для новых типов назначений

**Ключевые улучшения:**
1. **Автоматическое создание записей результатов** при создании назначений
2. **Полная синхронизация отмены** между examination_management, lab_tests и instrumental_procedures
3. **Единообразный статус отмены** во всех приложениях
4. **Сохранение причины отмены** с передачей между приложениями
