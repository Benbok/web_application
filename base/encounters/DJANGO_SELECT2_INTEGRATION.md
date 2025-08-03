# Интеграция django_select2 в encounters

## Обзор

В приложении `encounters` была успешно интегрирована библиотека `django_select2` для улучшения пользовательского интерфейса поля выбора диагноза. Это обеспечивает:

- Поиск по диагнозам с автодополнением
- Улучшенный пользовательский интерфейс
- Более удобную навигацию по большому количеству диагнозов

## Изменения в коде

### 1. Обновление форм (`encounters/forms.py`)

```python
from django_select2.forms import Select2Widget

class EncounterForm(forms.ModelForm):
    diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.all(),
        required=False,
        label="Диагноз",
        empty_label="Выберите диагноз",
        widget=Select2Widget(attrs={'class': 'form-select', 'id': 'diagnosis-select'})
    )
    
    class Meta:
        model = Encounter
        fields = ['date_start', 'diagnosis']
        widgets = {
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
```

### 2. Обновление базового шаблона (`patients/templates/patients/base.html`)

Добавлены CSS и JavaScript файлы для django_select2:

```html
<!-- В head -->
{{ form.media.css }}

<!-- В конце body -->
{{ form.media.js }}
```

### 3. Обновление JavaScript (`encounters/static/encounters/js/treatment_regimens.js`)

Добавлена поддержка событий Select2:

```javascript
initSelect2() {
    // Ждем инициализации Select2
    const checkSelect2 = () => {
        const diagnosisSelect = document.getElementById('diagnosis-select');
        if (diagnosisSelect && diagnosisSelect.classList.contains('django-select2')) {
            console.log('Select2 инициализирован');
            
            // Добавляем обработчик для Select2
            $(diagnosisSelect).on('select2:select', (e) => {
                console.log('Select2 выбрано:', e.params.data);
                this.onDiagnosisChange(e.params.data.id);
            });
            
            $(diagnosisSelect).on('select2:clear', () => {
                console.log('Select2 очищено');
                this.clearRegimensDisplay();
            });
        } else {
            setTimeout(checkSelect2, 100);
        }
    };
    
    checkSelect2();
}
```

## Конфигурация

### 1. Установка

`django_select2` уже установлен в проекте:
```
django-select2==8.4.1
```

### 2. Настройки Django

В `base/settings.py` уже добавлено:
```python
THIRD_PARTY_APPS = [
    'django_select2',
    # ...
]
```

### 3. URL-конфигурация

В `base/urls.py` уже добавлено:
```python
urlpatterns = [
    path('select2/', include('django_select2.urls')),
    # ...
]
```

## Функциональность

### 1. Поиск диагнозов

- Пользователь может вводить код или название диагноза
- Автодополнение предлагает подходящие варианты
- Поддержка кириллицы

### 2. Интеграция со схемами лечения

- При выборе диагноза автоматически загружаются схемы лечения
- Поддержка как обычных событий `change`, так и событий Select2
- Очистка отображения при сбросе выбора

### 3. Совместимость

- Обратная совместимость с обычными select элементами
- Делегирование событий для надежности
- Поддержка как новых, так и существующих форм

## Тестирование

### 1. Проверка конфигурации

```bash
python test_form_select2.py
```

### 2. Проверка API

```bash
python debug_encounter_api.py
```

### 3. Проверка в браузере

1. Откройте форму создания/редактирования encounter
2. Нажмите на поле "Диагноз"
3. Введите "J03" или "тонзиллит"
4. Выберите диагноз из выпадающего списка
5. Проверьте, что схемы лечения загрузились

## Отладка

### 1. Проверка консоли браузера

Откройте Developer Tools (F12) и проверьте консоль на наличие:
- Сообщений об инициализации Select2
- Сообщений о выборе диагноза
- Ошибок JavaScript

### 2. Проверка сетевых запросов

В Developer Tools -> Network проверьте:
- Запросы к `/select2/` для загрузки Select2
- Запросы к `/encounters/api/treatment-regimens/` при выборе диагноза

### 3. Проверка HTML

Убедитесь, что в HTML присутствуют атрибуты Select2:
```html
<select class="form-select django-select2" data-minimum-input-length="0" ...>
```

## Возможные проблемы

### 1. Select2 не инициализируется

**Причина**: CSS/JS файлы не загружены
**Решение**: Проверьте, что `{{ form.media.css }}` и `{{ form.media.js }}` добавлены в шаблон

### 2. События не срабатывают

**Причина**: Конфликт обработчиков событий
**Решение**: Используйте делегирование событий и обработчики Select2

### 3. Поиск не работает

**Причина**: Проблемы с кодировкой или настройками
**Решение**: Проверьте настройки языка и кодировки в Django

## Заключение

Интеграция `django_select2` успешно завершена. Поле выбора диагноза теперь предоставляет улучшенный пользовательский интерфейс с поиском и автодополнением, что особенно важно при работе с большим количеством диагнозов (более 11,000 записей).

Функциональность загрузки схем лечения при выборе диагноза полностью сохранена и улучшена для работы с Select2. 