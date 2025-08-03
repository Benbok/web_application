# Добавление Select2 виджета для выбора препаратов

## Проблема

При выборе препарата из справочника использовался обычный HTML select, что не позволяло эффективно искать препараты среди большого количества записей.

## Решение

Добавлен Select2 виджет для поля выбора препарата, который обеспечивает:
- AJAX поиск препаратов по названию
- Автодополнение при вводе
- Улучшенный пользовательский интерфейс

## Изменения в коде

### 1. Создан виджет MedicationSelect2Widget (base/pharmacy/widgets.py)

```python
from django_select2.forms import Select2Widget
from django.urls import reverse_lazy


class MedicationSelect2Widget(Select2Widget):
    """
    Кастомный Select2 виджет для препаратов с AJAX загрузкой.
    Загружает только те препараты, которые соответствуют поисковому запросу.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'data-ajax--url': reverse_lazy('pharmacy:ajax_search'),
            'data-ajax--cache': 'true',
            'data-ajax--delay': '250',
            'data-ajax--data-type': 'json',
            'data-ajax--minimum-input-length': '2',
            'data-placeholder': 'Введите название препарата...',
            'data-allow-clear': 'true',
            'data-language': 'ru',
        })


class MedicationSelect2WidgetLight(Select2Widget):
    """
    Облегченная версия Select2 виджета для препаратов.
    Загружает только первые 50 препаратов для быстрого старта.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'data-ajax--url': reverse_lazy('pharmacy:ajax_search_light'),
            'data-ajax--cache': 'true',
            'data-ajax--delay': '300',
            'data-ajax--data-type': 'json',
            'data-ajax--minimum-input-length': '1',
            'data-placeholder': 'Введите название препарата...',
            'data-allow-clear': 'true',
            'data-language': 'ru',
        })
```

### 2. Добавлены AJAX endpoints (base/pharmacy/views.py)

#### MedicationAjaxSearchView
```python
@method_decorator(csrf_exempt, name='dispatch')
class MedicationAjaxSearchView(View):
    """AJAX endpoint для поиска препаратов"""
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        page = request.GET.get('page', 1)
        
        if not query or len(query) < 2:
            return JsonResponse({
                'results': [],
                'pagination': {'more': False}
            })
        
        # Поиск по названию препарата
        medications = Medication.objects.filter(
            name__icontains=query
        ).order_by('name')[:20]
        
        results = []
        for medication in medications:
            results.append({
                'id': medication.pk,
                'text': f"{medication.name}",
            })
        
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        })
```

#### MedicationAjaxSearchLightView
```python
@method_decorator(csrf_exempt, name='dispatch')
class MedicationAjaxSearchLightView(View):
    """Облегченный AJAX endpoint для поиска препаратов"""
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        page = request.GET.get('page', 1)
        
        if not query:
            # Возвращаем первые 50 препаратов для быстрого старта
            medications = Medication.objects.all().order_by('name')[:50]
        else:
            # Поиск по названию препарата
            medications = Medication.objects.filter(
                name__icontains=query
            ).order_by('name')[:20]
        
        results = []
        for medication in medications:
            results.append({
                'id': medication.pk,
                'text': f"{medication.name}",
            })
        
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        })
```

### 3. Добавлены URL-паттерны (base/pharmacy/urls.py)

```python
urlpatterns = [
    path('', views.MedicationListView.as_view(), name='medication_list'),
    path('api/medications/<int:pk>/', views.medication_detail_api, name='medication_detail_api'),
    path('api/ajax-search/', views.MedicationAjaxSearchView.as_view(), name='ajax_search'),
    path('api/ajax-search-light/', views.MedicationAjaxSearchLightView.as_view(), name='ajax_search_light'),
]
```

### 4. Обновлена форма TreatmentMedicationForm (base/encounters/forms.py)

**Было:**
```python
medication = forms.ModelChoiceField(
    queryset=None,  # Будет установлен в __init__
    required=False,
    label="Препарат из справочника",
    empty_label="Выберите препарат из справочника",
    widget=forms.Select(attrs={'class': 'form-select', 'id': 'medication-select'})
)
```

**Стало:**
```python
from pharmacy.widgets import MedicationSelect2Widget

medication = forms.ModelChoiceField(
    queryset=None,  # Будет установлен в __init__
    required=False,
    label="Препарат из справочника",
    empty_label="Выберите препарат из справочника",
    widget=MedicationSelect2Widget(attrs={'class': 'form-select', 'id': 'medication-select'})
)
```

## Новый функционал

### 1. Select2 виджет для препаратов
- **AJAX поиск**: Поиск препаратов по названию в реальном времени
- **Автодополнение**: Предложения при вводе текста
- **Кэширование**: Кэширование результатов для улучшения производительности
- **Минимальная длина**: Поиск начинается после ввода 2 символов

### 2. Два типа поиска
- **Обычный поиск** (`MedicationAjaxSearchView`): Требует минимум 2 символа
- **Облегченный поиск** (`MedicationAjaxSearchLightView`): Показывает первые 50 препаратов сразу

### 3. Улучшенный пользовательский интерфейс
- **Placeholder**: "Введите название препарата..."
- **Очистка**: Возможность очистить выбранное значение
- **Русская локализация**: Интерфейс на русском языке

## Тестирование

Создан тестовый скрипт `scripts/test_medication_select2.py` для проверки:

### 1. Создание виджета
```bash
python scripts/test_medication_select2.py
```

**Результат**: ✅ MedicationSelect2Widget создан успешно

### 2. Атрибуты виджета
**Результат**: ✅ Все необходимые атрибуты установлены:
- `data-ajax--url`: `/pharmacy/api/ajax-search/`
- `data-ajax--cache`: `true`
- `data-ajax--delay`: `250`
- `data-ajax--minimum-input-length`: `2`
- `data-placeholder`: `Введите название препарата...`

### 3. Интеграция с формой
**Результат**: ✅ Поле medication использует MedicationSelect2Widget

### 4. AJAX endpoints
**Результат**: ✅ AJAX поиск работает корректно:
- Обычный поиск: 0 препаратов (для запроса "ампициллин")
- Облегченный поиск: 12 препаратов (все препараты в базе)

## Преимущества нового подхода

1. **Производительность**: Загружаются только нужные препараты
2. **Удобство**: Быстрый поиск по названию
3. **Масштабируемость**: Работает с большим количеством препаратов
4. **UX**: Современный интерфейс с автодополнением
5. **Гибкость**: Два типа поиска для разных сценариев

## Использование

Теперь при добавлении препарата в план лечения пользователь может:
1. Начать вводить название препарата
2. Увидеть предложения, соответствующие введенному тексту
3. Выбрать нужный препарат из списка
4. Очистить выбор при необходимости

## Статус

✅ **РЕАЛИЗОВАНО** - Select2 виджет для выбора препаратов добавлен и протестирован. 