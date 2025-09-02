# Интеграция системы дизайна с Django

## Обзор

Данный документ описывает процесс интеграции унифицированной системы дизайна "МедКарт" с Django-фреймворком. Интеграция обеспечивает автоматическое применение стилей и компонентов ко всем формам и страницам приложения.

## 1. Настройка базового шаблона

### Обновление base.html

```html
{% load static %}

<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}МедКарт | Личный кабинет врача{% endblock %}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Animate.css -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">
    
    <!-- Дизайн-токены и базовые стили -->
    <link rel="stylesheet" href="{% static 'css/design-tokens.css' %}">
    <link rel="stylesheet" href="{% static 'css/components.css' %}">
    
    <!-- Основные стили приложения -->
    <link rel="stylesheet" href="{% static 'patients/css/style.css' %}">
    
    <!-- Дополнительные CSS блоки -->
    {% block extra_css %}{% endblock %}
    
    <!-- Django Select2 CSS -->
    {{ form.media.css }}
</head>
<body class="app-body">
    <!-- Preloader -->
    <div class="preloader">
        <div class="preloader-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    </div>

    <div class="app-container">
        <!-- Sidebar -->
        <aside class="app-sidebar">
            <!-- Содержимое сайдбара -->
        </aside>
        
        <!-- Main Content -->
        <main class="app-main">
            <!-- Header -->
            <header class="app-header">
                <!-- Содержимое заголовка -->
            </header>
            
            <!-- Page Content -->
            <div class="app-content">
                {% block content %}{% endblock %}
            </div>
        </main>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    
    <!-- Основные скрипты приложения -->
    <script src="{% static 'js/app.js' %}"></script>
    
    <!-- Дополнительные JavaScript блоки -->
    {% block extra_js %}{% endblock %}
    
    <!-- Django Select2 JS -->
    {{ form.media.js }}
</body>
</html>
```

## 2. Создание CSS файлов

### design-tokens.css

```css
/* Дизайн-токены МедКарт */
:root {
    /* Основные цвета */
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --danger-color: #dc3545;
    --info-color: #17a2b8;
    
    /* Нейтральные цвета */
    --light-color: #f8f9fa;
    --dark-color: #343a40;
    --text-primary: #2c3e50;
    --text-secondary: #7f8c8d;
    --border-color: #e1e8ed;
    --shadow-color: rgba(0, 0, 0, 0.1);
    
    /* Градиенты */
    --gradient-primary: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    --gradient-success: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    --gradient-warning: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
    --gradient-danger: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%);
    
    /* Размеры */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
    --spacing-3xl: 4rem;
    
    /* Радиусы скругления */
    --border-radius-sm: 0.25rem;
    --border-radius-md: 0.375rem;
    --border-radius-lg: 0.5rem;
    --border-radius-xl: 0.75rem;
    --border-radius-2xl: 1rem;
    
    /* Тени */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    
    /* Анимации */
    --transition-fast: 150ms ease-out;
    --transition-normal: 300ms ease-out;
    --transition-slow: 500ms ease-out;
}
```

### components.css

```css
/* Унифицированные компоненты форм */
.form-container {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--spacing-lg);
}

.form-card {
    background: var(--light-color);
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-md);
    border: none;
    overflow: hidden;
}

.form-header {
    background: var(--gradient-primary);
    color: white;
    padding: var(--spacing-lg);
    border-bottom: none;
}

.form-header .card-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
}

.form-body {
    padding: var(--spacing-xl);
}

.form-fields {
    display: grid;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
}

.form-label {
    font-weight: 500;
    color: var(--text-primary);
    font-size: 1rem;
    margin-bottom: var(--spacing-xs);
}

.required-indicator {
    color: var(--danger-color);
    margin-left: var(--spacing-xs);
}

.form-control {
    height: 2.5rem;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-md);
    font-size: 1rem;
    transition: var(--transition-fast);
    background: var(--light-color);
}

.form-control:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    outline: none;
}

.form-control.is-invalid {
    border-color: var(--danger-color);
    box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.form-actions {
    display: flex;
    gap: var(--spacing-md);
    justify-content: flex-start;
    align-items: center;
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--border-color);
}

.form-actions .btn {
    min-width: 120px;
    height: 2.5rem;
    font-weight: 500;
    transition: var(--transition-normal);
}

/* Адаптивность */
@media (max-width: 768px) {
    .form-container {
        padding: var(--spacing-md);
    }
    
    .form-body {
        padding: var(--spacing-lg);
    }
    
    .form-actions {
        flex-direction: column;
        gap: var(--spacing-sm);
    }
    
    .form-actions .btn {
        width: 100%;
    }
}
```

## 3. Создание Django форм с автоматическими стилями

### Базовый класс формы

```python
# forms.py
from django import forms
from django.forms import ModelForm
from django.utils.html import mark_safe

class UnifiedFormMixin:
    """Миксин для унификации стилей форм"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_unified_styles()
    
    def apply_unified_styles(self):
        """Применяет унифицированные стили ко всем полям формы"""
        for field_name, field in self.fields.items():
            # Базовые CSS классы
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, forms.URLInput)):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label if field.label else '',
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': field.label if field.label else '',
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select',
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'form-check-input',
                })
            elif isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({
                    'class': 'form-check-input',
                })
            
            # Добавляем aria-label для доступности
            if field.label:
                field.widget.attrs.setdefault('aria-label', field.label)
            
            # Добавляем required атрибут
            if field.required:
                field.widget.attrs['required'] = 'required'

class UnifiedModelForm(UnifiedFormMixin, ModelForm):
    """Базовый класс для всех ModelForm с унифицированными стилями"""
    pass

class UnifiedForm(UnifiedFormMixin, forms.Form):
    """Базовый класс для всех Form с унифицированными стилями"""
    pass
```

### Пример использования

```python
# patients/forms.py
from django import forms
from .models import Patient
from base.forms import UnifiedModelForm

class PatientForm(UnifiedModelForm):
    class Meta:
        model = Patient
        fields = ['last_name', 'first_name', 'middle_name', 'birth_date', 'phone', 'email']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Дополнительная кастомизация полей
        self.fields['birth_date'].widget.attrs.update({
            'type': 'date',
            'max': '2025-12-31',
        })
        
        self.fields['phone'].widget.attrs.update({
            'type': 'tel',
            'pattern': r'\+7\s?\(?(\d{3})\)?\s?(\d{3})-?(\d{2})-?(\d{2})',
            'placeholder': '+7 (999) 123-45-67',
        })
        
        self.fields['email'].widget.attrs.update({
            'type': 'email',
            'placeholder': 'example@email.com',
        })
```

## 4. Создание шаблонных тегов

### Кастомные теги для форм

```python
# templatetags/form_tags.py
from django import template
from django.forms import BoundField
from django.utils.html import format_html

register = template.Library()

@register.filter
def add_form_classes(field):
    """Добавляет CSS классы к полю формы"""
    if isinstance(field, BoundField):
        widget = field.field.widget
        attrs = widget.attrs.copy()
        
        # Базовые классы
        if 'class' not in attrs:
            attrs['class'] = ''
        
        # Добавляем классы в зависимости от типа поля
        if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.NumberInput)):
            attrs['class'] += ' form-control'
        elif isinstance(widget, forms.Textarea):
            attrs['class'] += ' form-control'
        elif isinstance(widget, forms.Select):
            attrs['class'] += ' form-select'
        elif isinstance(widget, forms.CheckboxInput):
            attrs['class'] += ' form-check-input'
        
        # Добавляем класс для ошибок
        if field.errors:
            attrs['class'] += ' is-invalid'
        
        widget.attrs = attrs
        return field
    
    return field

@register.simple_tag
def render_field(field, label_class='form-label', help_class='form-text'):
    """Рендерит поле формы с унифицированными стилями"""
    html = f'<div class="form-group">'
    
    # Label
    if field.label:
        required = ' <span class="required-indicator">*</span>' if field.field.required else ''
        html += f'<label for="{field.id_for_label}" class="{label_class}">{field.label}{required}</label>'
    
    # Field
    html += f'{field}'
    
    # Help text
    if field.help_text:
        html += f'<div class="{help_class}">{field.help_text}</div>'
    
    # Errors
    if field.errors:
        html += f'<div class="invalid-feedback">'
        for error in field.errors:
            html += f'<div>{error}</div>'
        html += '</div>'
    
    html += '</div>'
    return format_html(html)

@register.simple_tag
def render_form_section(title, icon=None):
    """Рендерит секцию формы с заголовком"""
    html = f'<div class="form-section">'
    if icon:
        html += f'<h5 class="section-title"><i class="{icon} me-2"></i>{title}</h5>'
    else:
        html += f'<h5 class="section-title">{title}</h5>'
    html += '<div class="form-fields">'
    return format_html(html)

@register.simple_tag
def end_form_section():
    """Закрывает секцию формы"""
    return format_html('</div></div>')
```

## 5. Создание контекстных процессоров

### Автоматическое добавление переменных

```python
# context_processors.py
from django.conf import settings

def design_system(request):
    """Добавляет переменные системы дизайна в контекст"""
    return {
        'DESIGN_SYSTEM': {
            'version': '1.0',
            'theme': getattr(settings, 'DESIGN_THEME', 'light'),
            'primary_color': '#667eea',
            'secondary_color': '#764ba2',
        }
    }

def form_context(request):
    """Добавляет контекст для форм"""
    return {
        'FORM_DEFAULTS': {
            'cancel_url': request.META.get('HTTP_REFERER', '/'),
            'show_help_text': True,
            'show_required_indicators': True,
        }
    }
```

### Настройка в settings.py

```python
# settings.py
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'base.context_processors.design_system',
                'base.context_processors.form_context',
            ],
        },
    },
]

# Настройки системы дизайна
DESIGN_SYSTEM = {
    'VERSION': '1.0',
    'THEME': 'light',  # light, dark
    'PRIMARY_COLOR': '#667eea',
    'SECONDARY_COLOR': '#764ba2',
    'ENABLE_ANIMATIONS': True,
    'ENABLE_ACCESSIBILITY': True,
}
```

## 6. Создание миксинов для views

### Автоматическое применение стилей

```python
# mixins.py
from django.views.generic import CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy

class UnifiedFormMixin:
    """Миксин для унификации форм в views"""
    
    def get_form_class(self):
        """Возвращает форму с унифицированными стилями"""
        form_class = super().get_form_class()
        if hasattr(form_class, 'apply_unified_styles'):
            form_class.apply_unified_styles()
        return form_class
    
    def get_context_data(self, **kwargs):
        """Добавляет контекст для унифицированных форм"""
        context = super().get_context_data(**kwargs)
        
        # Добавляем заголовок формы
        if hasattr(self, 'form_title'):
            context['form_title'] = self.form_title
        else:
            if hasattr(self, 'model'):
                if self.object:
                    context['form_title'] = f'Редактировать {self.model._meta.verbose_name}'
                else:
                    context['form_title'] = f'Создать {self.model._meta.verbose_name}'
        
        # Добавляем подзаголовок
        if hasattr(self, 'form_subtitle'):
            context['form_subtitle'] = self.form_subtitle
        
        # Добавляем URL для отмены
        if hasattr(self, 'cancel_url'):
            context['cancel_url'] = self.cancel_url
        elif hasattr(self, 'success_url'):
            context['cancel_url'] = self.success_url
        
        return context
    
    def form_valid(self, form):
        """Обработка успешной отправки формы"""
        response = super().form_valid(form)
        
        # Добавляем сообщение об успехе
        if self.object:
            messages.success(self.request, f'{self.model._meta.verbose_name} успешно обновлен.')
        else:
            messages.success(self.request, f'{self.model._meta.verbose_name} успешно создан.')
        
        return response

class UnifiedCreateView(UnifiedFormMixin, CreateView):
    """Базовый класс для создания объектов с унифицированными формами"""
    template_name = 'unified_form.html'

class UnifiedUpdateView(UnifiedFormMixin, UpdateView):
    """Базовый класс для редактирования объектов с унифицированными формами"""
    template_name = 'unified_form.html'
```

### Пример использования

```python
# patients/views.py
from django.views.generic import ListView
from .models import Patient
from .forms import PatientForm
from base.mixins import UnifiedCreateView, UnifiedUpdateView

class PatientCreateView(UnifiedCreateView):
    model = Patient
    form_class = PatientForm
    success_url = reverse_lazy('patients:patient_list')
    cancel_url = reverse_lazy('patients:patient_list')
    
    def get_form_title(self):
        return 'Создать пациента'
    
    def get_form_subtitle(self):
        return 'Заполните основную информацию о пациенте'

class PatientUpdateView(UnifiedUpdateView):
    model = Patient
    form_class = PatientForm
    success_url = reverse_lazy('patients:patient_list')
    cancel_url = reverse_lazy('patients:patient_list')
    
    def get_form_title(self):
        return f'Редактировать пациента: {self.object.get_full_name()}'
```

## 7. Создание унифицированного шаблона формы

### unified_form.html

```html
{% extends "patients/base.html" %}
{% load form_tags %}

{% block title %}{{ form_title }} | МедКарт{% endblock %}

{% block content %}
<div class="form-container">
    <div class="card form-card">
        <div class="card-header form-header">
            <h4 class="card-title">{{ form_title }}</h4>
            {% if form_subtitle %}
                <p class="card-subtitle">{{ form_subtitle }}</p>
            {% endif %}
        </div>
        
        <div class="card-body form-body">
            {% if messages %}
                <div class="messages-container">
                    {% for message in messages %}
                        <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
            
            <form method="post" novalidate class="unified-form">
                {% csrf_token %}
                
                {% if form.non_field_errors %}
                    <div class="alert alert-danger">
                        {% for error in form.non_field_errors %}
                            {{ error }}
                        {% endfor %}
                    </div>
                {% endif %}
                
                <div class="form-fields">
                    {% for field in form.visible_fields %}
                        {% render_field field %}
                    {% endfor %}
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save me-2"></i>
                        {% if object %}Обновить{% else %}Создать{% endif %}
                    </button>
                    <a href="{{ cancel_url|default:'javascript:history.back()' }}" class="btn btn-secondary">
                        <i class="fas fa-times me-2"></i>Отмена
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

## 8. Настройка статических файлов

### Структура статических файлов

```
static/
├── css/
│   ├── design-tokens.css
│   ├── components.css
│   └── app.css
├── js/
│   ├── app.js
│   ├── forms.js
│   └── components.js
└── images/
    ├── logo.png
    └── icons/
```

### Настройка в settings.py

```python
# settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Сборка статических файлов
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
```

## 9. Создание команд управления

### Команда для создания компонентов

```python
# management/commands/create_component.py
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Создает новый компонент системы дизайна'
    
    def add_arguments(self, parser):
        parser.add_argument('component_name', type=str, help='Название компонента')
        parser.add_argument('--type', type=str, default='form', choices=['form', 'card', 'button', 'modal'], help='Тип компонента')
    
    def handle(self, *args, **options):
        component_name = options['component_name']
        component_type = options['type']
        
        # Создаем шаблон
        template_content = self.generate_template(component_name, component_type)
        template_path = f'templates/components/{component_name}.html'
        
        # Создаем CSS
        css_content = self.generate_css(component_name, component_type)
        css_path = f'static/css/components/{component_name}.css'
        
        # Создаем JavaScript
        js_content = self.generate_js(component_name, component_type)
        js_path = f'static/js/components/{component_name}.js'
        
        # Записываем файлы
        self.write_file(template_path, template_content)
        self.write_file(css_path, css_content)
        self.write_file(js_path, js_content)
        
        self.stdout.write(
            self.style.SUCCESS(f'Компонент {component_name} успешно создан!')
        )
    
    def generate_template(self, name, type):
        return render_to_string('component_templates/base.html', {
            'component_name': name,
            'component_type': type,
        })
    
    def generate_css(self, name, type):
        return f'/* Стили для компонента {name} */\n.{name} {{\n    /* Добавьте стили здесь */\n}}'
    
    def generate_js(self, name, type):
        return f'// JavaScript для компонента {name}\nclass {name.title()} {{\n    constructor() {{\n        this.init();\n    }}\n    \n    init() {{\n        // Инициализация компонента\n    }}\n}}'
    
    def write_file(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
```

## 10. Тестирование интеграции

### Тесты для форм

```python
# tests/test_forms.py
from django.test import TestCase
from django.test.client import RequestFactory
from patients.forms import PatientForm
from patients.models import Patient

class UnifiedFormTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
    
    def test_form_has_unified_styles(self):
        """Проверяет, что форма имеет унифицированные стили"""
        form = PatientForm()
        
        # Проверяем CSS классы
        for field_name, field in form.fields.items():
            if hasattr(field.widget, 'attrs'):
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput)):
                    self.assertIn('form-control', field.widget.attrs.get('class', ''))
                elif isinstance(field.widget, forms.Select):
                    self.assertIn('form-select', field.widget.attrs.get('class', ''))
    
    def test_form_validation(self):
        """Проверяет валидацию формы"""
        data = {
            'last_name': 'Иванов',
            'first_name': 'Иван',
            'birth_date': '1990-01-01',
        }
        form = PatientForm(data=data)
        self.assertTrue(form.is_valid())
    
    def test_form_errors_display(self):
        """Проверяет отображение ошибок формы"""
        data = {
            'last_name': '',  # Обязательное поле
        }
        form = PatientForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)
```

### Тесты для шаблонов

```python
# tests/test_templates.py
from django.test import TestCase
from django.urls import reverse
from patients.models import Patient

class UnifiedFormTemplateTestCase(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            last_name='Иванов',
            first_name='Иван',
            birth_date='1990-01-01'
        )
    
    def test_form_template_uses_unified_styles(self):
        """Проверяет, что шаблон формы использует унифицированные стили"""
        response = self.client.get(reverse('patients:patient_update', kwargs={'pk': self.patient.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form-container')
        self.assertContains(response, 'form-card')
        self.assertContains(response, 'form-header')
        self.assertContains(response, 'form-body')
    
    def test_form_has_required_indicators(self):
        """Проверяет наличие индикаторов обязательных полей"""
        response = self.client.get(reverse('patients:patient_create'))
        
        self.assertContains(response, 'required-indicator')
        self.assertContains(response, '*')
```

## 11. Документация для разработчиков

### README для интеграции

```markdown
# Интеграция системы дизайна с Django

## Быстрый старт

1. Установите статические файлы:
```bash
python manage.py collectstatic
```

2. Создайте форму с унифицированными стилями:
```python
from base.forms import UnifiedModelForm
from .models import YourModel

class YourModelForm(UnifiedModelForm):
    class Meta:
        model = YourModel
        fields = ['field1', 'field2', 'field3']
```

3. Создайте view:
```python
from base.mixins import UnifiedCreateView

class YourModelCreateView(UnifiedCreateView):
    model = YourModel
    form_class = YourModelForm
    success_url = reverse_lazy('your_app:list')
```

4. Используйте унифицированный шаблон:
```python
# В urls.py
path('create/', YourModelCreateView.as_view(), name='create')
```

## Кастомизация

### Изменение цветов
Отредактируйте `static/css/design-tokens.css`

### Добавление новых компонентов
Используйте команду:
```bash
python manage.py create_component component_name --type form
```

### Создание кастомных форм
Наследуйтесь от `UnifiedFormMixin` и переопределите `apply_unified_styles()`
```

## 12. Мониторинг и аналитика

### Отслеживание использования компонентов

```python
# middleware.py
import time
from django.utils.deprecation import MiddlewareMixin

class DesignSystemMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.design_system_start = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, 'design_system_start'):
            duration = time.time() - request.design_system_start
            
            # Логируем использование системы дизайна
            if 'unified-form' in response.content.decode():
                logger.info(f'Unified form used: {request.path} ({duration:.2f}s)')
        
        return response
```

---

**Дата создания**: 28.08.2025  
**Версия**: 1.0  
**Статус**: Активная интеграция  
**Ответственный**: Backend разработчик
