# Добавление кнопок быстрого добавления препаратов из рекомендаций

## Проблема

В списке рекомендаций по лечению пользователь мог видеть рекомендованные препараты, но не мог быстро добавить их в план лечения. Требовалось переходить в каждый план лечения отдельно и добавлять препараты вручную.

## Решение

Добавлены кнопки "Добавить" для каждого рекомендованного препарата в списке рекомендаций, которые позволяют быстро добавить препарат в выбранный план лечения.

## Изменения в коде

### 1. Новое представление QuickAddMedicationView (base/encounters/views.py)

```python
class QuickAddMedicationView(CreateView):
    """Представление для быстрого добавления препарата из рекомендаций"""
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'encounters/quick_add_medication.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs.get('plan_pk'))
        self.encounter = self.treatment_plan.encounter
        self.patient = self.encounter.patient
        
        # Получаем данные о препарате из рекомендации
        medication_id = self.kwargs.get('medication_id')
        if medication_id:
            from pharmacy.models import Medication
            try:
                self.recommended_medication = Medication.objects.get(pk=medication_id)
            except Medication.DoesNotExist:
                self.recommended_medication = None
        else:
            self.recommended_medication = None
    
    def get_initial(self):
        """Устанавливаем начальные значения из рекомендации"""
        initial = super().get_initial()
        if self.recommended_medication:
            initial['medication'] = self.recommended_medication
        return initial
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)
        messages.success(self.request, f'Препарат "{form.instance.get_medication_name()}" успешно добавлен в план лечения')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        context['encounter'] = self.encounter
        context['patient'] = self.patient
        context['recommended_medication'] = self.recommended_medication
        context['title'] = 'Быстрое добавление препарата'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.treatment_plan.pk})
```

### 2. Добавлен метод get_medication_name() в модель TreatmentMedication (base/encounters/models.py)

```python
def get_medication_name(self):
    """Возвращает название препарата"""
    if self.medication:
        return self.medication.name
    elif self.custom_medication:
        return self.custom_medication
    else:
        return "Неизвестный препарат"
```

### 3. Добавлен URL-паттерн (base/encounters/urls.py)

```python
path('plans/<int:plan_pk>/quick-add/<int:medication_id>/', views.QuickAddMedicationView.as_view(), name='quick_add_medication'),
```

### 4. Создан шаблон quick_add_medication.html

Новый шаблон для быстрого добавления препарата с:
- Предзаполненным полем препарата из рекомендации
- Информацией о рекомендуемом препарате
- JavaScript для скрытия поля custom_medication при выборе препарата из справочника

### 5. Обновлен шаблон treatment_plans.html

**Было:**
```html
<div class="card border-info">
    <div class="card-body py-2">
        <h6 class="card-title mb-1">{{ recommendation.medication.name }}</h6>
        <!-- информация о препарате -->
    </div>
</div>
```

**Стало:**
```html
<div class="card border-info">
    <div class="card-header d-flex justify-content-between align-items-center py-2">
        <h6 class="card-title mb-0">{{ recommendation.medication.name }}</h6>
        {% if treatment_plans %}
            <div class="dropdown">
                <button class="btn btn-sm btn-outline-success dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="fas fa-plus"></i> Добавить
                </button>
                <ul class="dropdown-menu">
                    {% for plan in treatment_plans %}
                        <li>
                            <a class="dropdown-item" href="{% url 'encounters:quick_add_medication' plan.pk recommendation.medication.id %}">
                                <i class="fas fa-pills"></i> {{ plan.name }}
                            </a>
                        </li>
                    {% endfor %}
                </ul>
            </div>
        {% endif %}
    </div>
    <div class="card-body py-2">
        <!-- информация о препарате -->
    </div>
</div>
```

## Новый функционал

### 1. Кнопки быстрого добавления
- **Dropdown меню**: Для каждого рекомендованного препарата добавлена кнопка "Добавить"
- **Выбор плана**: При нажатии на кнопку открывается dropdown с списком доступных планов лечения
- **Быстрый переход**: Прямой переход к форме добавления препарата в выбранный план

### 2. Форма быстрого добавления
- **Предзаполнение**: Поле препарата автоматически заполняется из рекомендации
- **Информация**: Показывается информация о рекомендуемом препарате
- **Удобство**: Поле custom_medication скрывается при выборе препарата из справочника

### 3. Улучшенный пользовательский интерфейс
- **Визуальное разделение**: Название препарата и кнопка добавления в header карточки
- **Интуитивность**: Понятные иконки и подписи
- **Адаптивность**: Работает на всех устройствах

## Тестирование

Создан тестовый скрипт `scripts/test_quick_add_medication.py` для проверки:

### 1. Быстрое добавление препарата
```bash
python scripts/test_quick_add_medication.py
```

**Результат**: ✅ Препарат успешно добавляется в план лечения

### 2. Метод get_medication_name
**Результат**: ✅ Метод корректно возвращает название препарата

### 3. URL-паттерны
**Результат**: ✅ URL для быстрого добавления работает корректно

## Преимущества нового подхода

1. **Скорость**: Быстрое добавление препаратов из рекомендаций
2. **Удобство**: Не нужно переходить в каждый план лечения отдельно
3. **Интуитивность**: Понятный интерфейс с dropdown меню
4. **Гибкость**: Выбор конкретного плана лечения для добавления
5. **Предзаполнение**: Автоматическое заполнение формы данными из рекомендации

## Использование

Теперь пользователь может:

1. **Просматривать рекомендации**: Видеть список рекомендованных препаратов
2. **Выбирать план**: Нажать кнопку "Добавить" и выбрать нужный план лечения
3. **Быстро добавлять**: Перейти к форме с предзаполненными данными
4. **Настраивать параметры**: При необходимости изменить дозировку, частоту и другие параметры
5. **Сохранять**: Добавить препарат в план лечения одним кликом

## Исправления

### Ошибка NoReverseMatch
Была исправлена ошибка `NoReverseMatch` при попытке генерации URL для препаратов с `None` ID.

**Проблема:**
```python
# В шаблоне treatment_plans.html
{% url 'encounters:quick_add_medication' plan.pk recommendation.medication.id %}
# Если recommendation.medication.id == None, возникала ошибка
```

**Решение:**
```html
{% if treatment_plans %}
    <div class="dropdown">
        <button class="btn btn-sm btn-outline-success dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="fas fa-plus"></i> Добавить
        </button>
        <ul class="dropdown-menu">
            {% for plan in treatment_plans %}
                <li>
                    {% if recommendation.medication.id %}
                        <a class="dropdown-item" href="{% url 'encounters:quick_add_medication' plan.pk recommendation.medication.id %}">
                            <i class="fas fa-pills"></i> {{ plan.name }}
                        </a>
                    {% else %}
                        <a class="dropdown-item" href="{% url 'encounters:quick_add_medication_by_name' plan.pk recommendation.medication.name %}">
                            <i class="fas fa-pills"></i> {{ plan.name }} (по названию)
                        </a>
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
    </div>
{% endif %}
```

### Добавление препаратов по названию
Добавлена возможность добавления препаратов, которые не найдены в справочнике, но имеют название в рекомендациях.

**Изменения в TreatmentPlanService:**
```python
# Ищем препарат в базе данных по названию
medication_obj = None
if medication:
    # Поиск по точному названию
    medication_obj = Medication.objects.filter(name__iexact=medication).first()
    if not medication_obj:
        # Поиск по частичному совпадению
        medication_obj = Medication.objects.filter(name__icontains=medication).first()

# Формируем рекомендацию
recommendation = {
    'medication': {
        'id': medication_obj.id if medication_obj else None,
        'name': medication
    },
    # ...
}
```

**Новый URL-паттерн:**
```python
path('plans/<int:plan_pk>/quick-add-by-name/<str:medication_name>/', views.QuickAddMedicationView.as_view(), name='quick_add_medication_by_name'),
```

**Обновление QuickAddMedicationView:**
```python
def get_initial(self):
    """Устанавливаем начальные значения из рекомендации"""
    initial = super().get_initial()
    if self.recommended_medication:
        initial['medication'] = self.recommended_medication
    else:
        # Если препарат не найден в базе, но есть название из рекомендации
        medication_name = self.kwargs.get('medication_name')
        if medication_name:
            initial['custom_medication'] = medication_name
    return initial
```

## Статус

✅ **РЕАЛИЗОВАНО** - Кнопки быстрого добавления препаратов из рекомендаций добавлены, протестированы и исправлены ошибки. 