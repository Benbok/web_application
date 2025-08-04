# Обновление: Внешние ссылки и поле "Особые указания"

## Описание изменений

Реализован функционал для автоматического заполнения поля "Особые указания" при выборе препарата и отображения ссылки на источник информации о препарате.

## Основные изменения

### 1. Обновление MedicationInfoView

**Файл:** `base/encounters/views.py`

- Добавлено поле `external_url` в ответ AJAX endpoint
- Поле `instructions` теперь заполняется из `regimen.notes`

```python
# Получаем информацию о препарате
medication_info = {
    'id': medication.id,
    'name': medication.name,
    'description': getattr(medication, 'description', ''),
    'external_url': medication.external_info_url or '',  # НОВОЕ
    'dosage': '',
    'frequency': '',
    'route': 'oral',
    'duration': '',
    'instructions': ''
}

# При заполнении данных из схемы
if regimen:
    dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
    if dosing_instruction:
        # ... другие поля ...
        medication_info['instructions'] = regimen.notes or ''  # ОБНОВЛЕНО
```

### 2. Обновление шаблонов форм

**Файлы:** 
- `base/encounters/templates/encounters/treatment_medication_form.html`
- `base/encounters/templates/encounters/quick_add_medication.html`

#### Добавлено поле для внешней ссылки:

```html
<!-- Поле для отображения ссылки на источник информации -->
<div class="mb-3" id="external-link-container" style="display: none;">
    <label class="form-label">Источник информации о препарате:</label>
    <div id="external-link-content">
        <a href="#" id="external-link" target="_blank" class="btn btn-outline-info btn-sm">
            <i class="fas fa-external-link-alt"></i> Открыть информацию о препарате
        </a>
    </div>
</div>
```

#### Обновлен JavaScript код:

```javascript
// Добавлены переменные для внешней ссылки
const externalLinkContainer = document.getElementById('external-link-container');
const externalLink = document.getElementById('external-link');

// В функции loadMedicationInfo добавлена обработка внешней ссылки
if (externalLinkContainer && externalLink) {
    if (med.external_url) {
        externalLink.href = med.external_url;
        externalLinkContainer.style.display = 'block';
    } else {
        externalLinkContainer.style.display = 'none';
    }
}

// При очистке полей также скрываем ссылку
if (externalLinkContainer) externalLinkContainer.style.display = 'none';
```

## Функционал удаления планов лечения

### 1. Новый View для удаления

**Файл:** `base/encounters/views.py`

```python
class TreatmentPlanDeleteView(DeleteView):
    """Представление для удаления плана лечения"""
    model = TreatmentPlan
    template_name = 'encounters/treatment_plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['medications'] = self.object.medications.all()
        context['title'] = 'Удалить план лечения'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.encounter.pk})
```

### 2. URL для удаления

**Файл:** `base/encounters/urls.py`

```python
path('treatment-plans/<int:pk>/delete/', views.TreatmentPlanDeleteView.as_view(), name='treatment_plan_delete'),
```

### 3. Шаблон подтверждения удаления

**Файл:** `base/encounters/templates/encounters/treatment_plan_confirm_delete.html`

- Показывает информацию о плане лечения
- Список лекарств, которые будут удалены
- Кнопки подтверждения и отмены

### 4. Кнопки удаления в интерфейсе

**Файлы:**
- `base/encounters/templates/encounters/treatment_plan_detail.html`
- `base/encounters/templates/encounters/treatment_plans.html`

Добавлены кнопки удаления:
```html
<a href="{% url 'encounters:treatment_plan_delete' treatment_plan.pk %}" class="btn btn-danger">
    <i class="fas fa-trash"></i> Удалить план
</a>
```

## Тестирование

### 1. Тест внешних ссылок и instructions

**Файл:** `base/scripts/test_external_links_and_instructions.py`

Проверяет:
- Наличие препаратов с внешними ссылками
- Схемы с примечаниями
- Корректность данных в AJAX ответе

### 2. Тест удаления планов лечения

**Файл:** `base/scripts/test_treatment_plan_delete.py`

Проверяет:
- Наличие планов лечения для удаления
- Корректность URL для удаления
- Симуляцию процесса удаления

## Результаты тестирования

### Внешние ссылки и instructions:
- ✅ 14 препаратов имеют внешние ссылки
- ✅ 33 схемы содержат примечания
- ✅ Поле instructions корректно заполняется из regimen.notes
- ✅ Внешние ссылки передаются в AJAX ответе

### Удаление планов лечения:
- ✅ 17 планов лечения в системе
- ✅ 6 случаев содержат планы лечения
- ✅ URL для удаления корректно формируется
- ✅ Функционал готов к использованию

## Использование

### При выборе препарата в форме:
1. Поле "Особые указания" автоматически заполняется примечаниями из выбранной схемы
2. Если у препарата есть внешняя ссылка, появляется кнопка "Открыть информацию о препарате"
3. При нажатии на кнопку ссылка открывается в новой вкладке

### Удаление плана лечения:
1. В списке планов лечения или в детальном просмотре плана нажать кнопку "Удалить"
2. Подтвердить удаление на странице подтверждения
3. После удаления произойдет редирект к списку планов лечения

## Технические детали

### Модель Medication (pharmacy/models.py):
```python
external_info_url = models.URLField(max_length=500, blank=True, null=True, 
                                   verbose_name=_("Ссылка на полную информацию о препарате"))
```

### Модель Regimen (pharmacy/models.py):
```python
notes = models.TextField(_("Общие примечания к схеме"), blank=True, null=True)
```

### AJAX Endpoint:
- URL: `/encounters/api/medication-info/<medication_id>/`
- Метод: GET
- Параметры: `patient_id` (опционально)
- Ответ включает: `external_url`, `instructions` 