# Интеграция формы настройки расписания

## Обзор

Система `clinical_scheduling` теперь включает форму для настройки параметров расписания назначений. После создания назначения (лекарства, лабораторного исследования, процедуры) пользователь автоматически перенаправляется на форму настройки расписания.

## Как это работает

1. **Пользователь создает назначение** (лекарство, лабораторное исследование, процедуру)
2. **Система перенаправляет на форму настройки расписания** с предзаполненными параметрами
3. **Пользователь настраивает параметры:**
   - Дата начала
   - Время первого приема
   - Количество приемов в день
   - Длительность курса
4. **Система создает записи в `ScheduledAppointment`** с указанными параметрами
5. **Пользователь перенаправляется на dashboard** с созданными записями

## Интеграция в существующие представления

### Вариант 1: Использование миксинов (рекомендуется)

Добавьте соответствующий миксин к вашему представлению:

```python
from clinical_scheduling.mixins import (
    MedicationScheduleRedirectMixin,
    LabTestScheduleRedirectMixin,
    ProcedureScheduleRedirectMixin
)

# Для лекарств
class TreatmentMedicationCreateView(LoginRequiredMixin, OwnerContextMixin, 
                                   MedicationScheduleRedirectMixin, CreateView):
    # ... ваш код ...

# Для лабораторных исследований
class ExaminationLabTestCreateView(LoginRequiredMixin, 
                                  LabTestScheduleRedirectMixin, CreateView):
    # ... ваш код ...

# Для процедур
class ExaminationInstrumentalCreateView(LoginRequiredMixin, 
                                       ProcedureScheduleRedirectMixin, CreateView):
    # ... ваш код ...
```

### Вариант 2: Ручная интеграция

В методе `form_valid` вашего представления:

```python
from clinical_scheduling.utils import redirect_to_schedule_settings

def form_valid(self, form):
    response = super().form_valid(form)
    
    # Ваша логика...
    
    # Перенаправляем на форму настройки расписания
    return redirect_to_schedule_settings(form.instance, 'medication')  # или 'lab_test', 'procedure'
```

## Доступные типы назначений

- `medication` - для лекарств (TreatmentMedication)
- `lab_test` - для лабораторных исследований (ExaminationLabTest)
- `procedure` - для процедур (ExaminationInstrumental)

## URL-адреса

- **Форма настройки:** `/scheduling/schedule-settings/`
- **Dashboard:** `/scheduling/`
- **Детали назначения:** `/scheduling/appointment/<id>/`

## Параметры формы

Форма автоматически адаптируется под тип назначения:

- **Лекарства:** длительность 7 дней, 2 приема в день по умолчанию
- **Лабораторные исследования:** длительность 1 день, 1 прием в день
- **Процедуры:** длительность 1 день, 1 прием в день

## Пример использования

```python
# В вашем представлении
from clinical_scheduling.mixins import MedicationScheduleRedirectMixin

class MyMedicationCreateView(LoginRequiredMixin, MedicationScheduleRedirectMixin, CreateView):
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'my_template.html'
    
    # Миксин автоматически перенаправит на форму настройки расписания
    # после успешного создания назначения
```

## Настройка по умолчанию

Если вы хотите изменить параметры по умолчанию, отредактируйте файл `base/clinical_scheduling/forms.py`:

```python
def __init__(self, *args, **kwargs):
    assignment_type = kwargs.pop('assignment_type', None)
    super().__init__(*args, **kwargs)
    
    if assignment_type == 'medication':
        self.fields['duration_days'].initial = 10  # изменить с 7 на 10
        self.fields['times_per_day'].initial = 3   # изменить с 2 на 3
```

## Обработка ошибок

Система автоматически обрабатывает ошибки и показывает пользователю понятные сообщения. Если что-то пойдет не так, пользователь будет перенаправлен на dashboard с соответствующим сообщением об ошибке. 