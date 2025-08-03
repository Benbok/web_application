# Изменение функционала планов лечения на ручной режим

## Проблема

При создании плана лечения все рекомендованные препараты автоматически добавлялись в создаваемый план, что не позволяло пользователю выбирать нужные препараты вручную.

## Решение

Изменен функционал создания планов лечения с автоматического на ручной режим, добавлена возможность редактирования и удаления препаратов.

## Изменения в коде

### 1. Представление TreatmentPlanCreateView (base/encounters/views.py)

**Было:**
```python
def form_valid(self, form):
    # Создаем план лечения с рекомендациями
    treatment_plan = TreatmentPlanService.create_treatment_plan_with_recommendations(
        encounter=self.encounter,
        name=form.cleaned_data['name'],
        description=form.cleaned_data.get('description', '')
    )
    
    messages.success(self.request, f'План лечения успешно создан: {treatment_plan.name}')
    
    # Перенаправляем на детальный просмотр созданного плана
    return redirect('encounters:treatment_plan_detail', pk=treatment_plan.pk)
```

**Стало:**
```python
def form_valid(self, form):
    # Создаем план лечения без автоматического добавления препаратов
    form.instance.encounter = self.encounter
    treatment_plan = form.save()
    
    messages.success(self.request, f'План лечения успешно создан: {treatment_plan.name}')
    
    # Перенаправляем на детальный просмотр созданного плана
    return redirect('encounters:treatment_plan_detail', pk=treatment_plan.pk)
```

### 2. Новые представления для управления препаратами

Добавлены новые представления в `base/encounters/views.py`:

#### TreatmentMedicationUpdateView
```python
class TreatmentMedicationUpdateView(UpdateView):
    """Представление для редактирования лекарства в плане лечения"""
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'encounters/treatment_medication_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['encounter'] = self.object.treatment_plan.encounter
        context['patient'] = self.object.treatment_plan.encounter.patient
        context['title'] = 'Редактировать лекарство'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.object.treatment_plan.pk})
```

#### TreatmentMedicationDeleteView
```python
class TreatmentMedicationDeleteView(DeleteView):
    """Представление для удаления лекарства из плана лечения"""
    model = TreatmentMedication
    template_name = 'encounters/treatment_medication_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['encounter'] = self.object.treatment_plan.encounter
        context['patient'] = self.object.treatment_plan.encounter.patient
        context['title'] = 'Удалить лекарство'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.object.treatment_plan.pk})
```

### 3. URL-паттерны (base/encounters/urls.py)

Добавлены новые URL-паттерны:
```python
path('medications/<int:pk>/edit/', views.TreatmentMedicationUpdateView.as_view(), name='treatment_medication_update'),
path('medications/<int:pk>/delete/', views.TreatmentMedicationDeleteView.as_view(), name='treatment_medication_delete'),
```

### 4. Шаблоны

#### Обновлен treatment_plan_detail.html
Добавлены кнопки редактирования и удаления для каждого препарата:
```html
<div class="btn-group btn-group-sm">
    <a href="{% url 'encounters:treatment_medication_update' medication.pk %}" class="btn btn-outline-primary btn-sm">
        <i class="fas fa-edit"></i>
    </a>
    <a href="{% url 'encounters:treatment_medication_delete' medication.pk %}" class="btn btn-outline-danger btn-sm">
        <i class="fas fa-trash"></i>
    </a>
</div>
```

#### Создан treatment_medication_confirm_delete.html
Новый шаблон для подтверждения удаления препарата с подробной информацией о препарате.

#### Обновлен treatment_plans.html
Добавлено пояснение о ручном добавлении рекомендованных препаратов:
```html
<div class="mt-3">
    <small class="text-muted">
        <i class="fas fa-info-circle"></i> 
        Вы можете добавить эти препараты в план лечения вручную, используя кнопку "Добавить лекарство" в каждом плане.
    </small>
</div>
```

## Новый функционал

### 1. Ручное создание плана лечения
- План лечения создается без автоматического добавления препаратов
- Пользователь может добавить препараты вручную после создания плана

### 2. Управление препаратами
- **Добавление**: Кнопка "Добавить лекарство" в каждом плане лечения
- **Редактирование**: Кнопка редактирования (иконка карандаша) для каждого препарата
- **Удаление**: Кнопка удаления (иконка корзины) для каждого препарата

### 3. Рекомендации
- Рекомендованные препараты отображаются в списке планов лечения
- Пользователь может выбрать нужные препараты и добавить их вручную
- Добавлено пояснение о ручном добавлении

## Тестирование

Создан тестовый скрипт `scripts/test_manual_treatment_plan.py` для проверки:

### 1. Ручное создание плана лечения
```bash
python scripts/test_manual_treatment_plan.py
```

**Результат**: ✅ План лечения создается без автоматического добавления препаратов

### 2. Ручное добавление препаратов
**Результат**: ✅ Препараты добавляются вручную с указанием дозировки, частоты, способа применения

### 3. Операции с препаратами
**Результат**: ✅ Редактирование и удаление препаратов работает корректно

## Преимущества нового подхода

1. **Гибкость**: Пользователь может выбирать нужные препараты из рекомендаций
2. **Контроль**: Полный контроль над составом плана лечения
3. **Редактирование**: Возможность изменения дозировки и других параметров
4. **Удаление**: Возможность удаления ненужных препаратов
5. **Прозрачность**: Понятный процесс создания плана лечения

## Статус

✅ **РЕАЛИЗОВАНО** - Функционал планов лечения изменен на ручной режим с возможностью редактирования и удаления препаратов. 