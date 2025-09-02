# Компоненты форм - МедКарт

## Обзор

Унифицированные компоненты форм для медицинской информационной системы МедКарт. Все формы следуют единому дизайну и используют design tokens для консистентности.

## Базовая структура формы

### HTML структура

```html
{% extends "patients/base.html" %}
{% load widget_tweaks %}

{% block title %}{{ title }} | МедКарт{% endblock %}

{% block content %}
<div class="form-container">
    <div class="card mt-4" style="z-index: 2;">
        <div class="card-body position-relative">
            <!-- Заголовок формы -->
            <h4 class="card-title mb-4">{{ title }}</h4>
            
            <!-- Форма -->
            <form method="post" class="medical-form">
                {% csrf_token %}
                
                <!-- Основная информация -->
                <div class="form-section">
                    <h5 class="section-title">
                        <i class="fas fa-info-circle me-2"></i>Основная информация
                    </h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.field1.id_for_label }}" class="form-label">
                                    <strong>{{ form.field1.label }}</strong>
                                </label>
                                {{ form.field1|add_class:"form-control" }}
                                {% if form.field1.help_text %}
                                    <small class="form-text text-muted">{{ form.field1.help_text }}</small>
                                {% endif %}
                                {% if form.field1.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.field1.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.field2.id_for_label }}" class="form-label">
                                    <strong>{{ form.field2.label }}</strong>
                                </label>
                                {{ form.field2|add_class:"form-control" }}
                                {% if form.field2.help_text %}
                                    <small class="form-text text-muted">{{ form.field2.help_text }}</small>
                                {% endif %}
                                {% if form.field2.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.field2.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Дополнительная информация -->
                <div class="form-section">
                    <h5 class="section-title">
                        <i class="fas fa-plus-circle me-2"></i>Дополнительная информация
                    </h5>
                    <div class="form-group">
                        <label for="{{ form.field3.id_for_label }}" class="form-label">
                            <strong>{{ form.field3.label }}</strong>
                        </label>
                        {{ form.field3|add_class:"form-control" }}
                        {% if form.field3.help_text %}
                            <small class="form-text text-muted">{{ form.field3.help_text }}</small>
                        {% endif %}
                        {% if form.field3.errors %}
                            <div class="invalid-feedback d-block">
                                {% for error in form.field3.errors %}
                                    {{ error }}
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                </div>

                <!-- Кнопки действий -->
                <div class="form-actions">
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <div class="btn-toolbar" role="toolbar" aria-label="Основные действия">
                            <div class="btn-group me-2" role="group">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save me-1"></i>Сохранить
                                </button>
                            </div>
                            <div class="btn-group me-2" role="group">
                                <a href="{{ cancel_url|default:'javascript:history.back()' }}" 
                                   class="btn btn-outline-secondary">
                                    <i class="fas fa-times me-1"></i>Отмена
                                </a>
                            </div>
                        </div>
                        
                        <div class="ms-auto">
                            <a href="{{ back_url|default:'javascript:history.back()' }}" 
                               class="btn btn-secondary">
                                <i class="fas fa-arrow-left me-1"></i>Назад
                            </a>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### CSS стили

```css
/* Контейнер формы */
.form-container {
    max-width: 1200px;
    margin: 0 auto;
}

/* Карточка формы */
.form-container .card {
    background-color: var(--bg-secondary);
    border: none;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-sm);
    transition: all var(--transition-speed) ease;
}

.form-container .card:hover {
    box-shadow: var(--shadow-hover);
}

/* Заголовок формы */
.form-container .card-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-lg);
    font-size: 1.25rem;
}

/* Секции формы */
.form-section {
    margin-bottom: var(--spacing-xl);
    padding: var(--spacing-lg);
    background-color: var(--bg-primary);
    border-radius: var(--border-radius);
    border-left: 3px solid var(--primary-color);
}

.section-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
    font-size: 1.1rem;
    display: flex;
    align-items: center;
}

.section-title i {
    color: var(--primary-color);
}

/* Группы полей */
.form-group {
    margin-bottom: var(--spacing-md);
}

.form-label {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-sm);
    font-size: 0.9rem;
}

.form-label strong {
    color: var(--text-primary);
}

/* Поля ввода */
.form-control {
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 0.9rem;
    transition: all var(--transition-fast) ease;
    background-color: var(--bg-secondary);
}

.form-control:focus {
    border-color: var(--primary-light);
    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
    outline: none;
}

.form-control:disabled {
    background-color: var(--bg-hover);
    color: var(--text-muted);
}

/* Текст помощи */
.form-text {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: var(--spacing-xs);
}

/* Ошибки */
.invalid-feedback {
    font-size: 0.8rem;
    color: var(--danger-color);
    margin-top: var(--spacing-xs);
}

/* Кнопки действий */
.form-actions {
    border-top: 1px solid var(--border-light);
    padding-top: var(--spacing-lg);
    margin-top: var(--spacing-lg);
}

.btn-toolbar {
    display: flex;
    gap: var(--spacing-sm);
}

.btn-group {
    display: flex;
    gap: var(--spacing-xs);
}

/* Кнопки */
.btn {
    border-radius: var(--border-radius);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 0.9rem;
    font-weight: 500;
    transition: all var(--transition-fast) ease;
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
}

.btn-primary {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background-color: var(--secondary-color);
    border-color: var(--secondary-color);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.btn-outline-secondary {
    color: var(--text-secondary);
    border-color: var(--border-color);
    background-color: transparent;
}

.btn-outline-secondary:hover {
    background-color: var(--bg-hover);
    border-color: var(--text-secondary);
    color: var(--text-primary);
}

.btn-secondary {
    background-color: var(--text-secondary);
    border-color: var(--text-secondary);
    color: white;
}

.btn-secondary:hover {
    background-color: var(--text-primary);
    border-color: var(--text-primary);
    transform: translateY(-1px);
}

/* Адаптивность */
@media (max-width: 768px) {
    .form-section {
        padding: var(--spacing-md);
    }
    
    .form-actions .d-flex {
        flex-direction: column;
        gap: var(--spacing-md);
    }
    
    .btn-toolbar {
        justify-content: center;
    }
    
    .ms-auto {
        margin-left: 0 !important;
        margin-top: var(--spacing-md);
    }
}
```

## Специализированные формы

### Форма пациента

```html
{% extends "patients/base.html" %}
{% load widget_tweaks %}

{% block title %}{{ title }} | МедКарт{% endblock %}

{% block content %}
<div class="form-container">
    <div class="card mt-4" style="z-index: 2;">
        <div class="card-body position-relative">
            <h4 class="card-title mb-4">{{ title }}</h4>
            
            <form method="post" class="patient-form">
                {% csrf_token %}
                
                <!-- Личные данные -->
                <div class="form-section">
                    <h5 class="section-title">
                        <i class="fas fa-user me-2"></i>Личные данные
                    </h5>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="form-group">
                                <label for="{{ form.last_name.id_for_label }}" class="form-label">
                                    <strong>{{ form.last_name.label }}</strong>
                                </label>
                                {{ form.last_name|add_class:"form-control" }}
                                {% if form.last_name.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.last_name.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label for="{{ form.first_name.id_for_label }}" class="form-label">
                                    <strong>{{ form.first_name.label }}</strong>
                                </label>
                                {{ form.first_name|add_class:"form-control" }}
                                {% if form.first_name.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.first_name.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label for="{{ form.middle_name.id_for_label }}" class="form-label">
                                    <strong>{{ form.middle_name.label }}</strong>
                                </label>
                                {{ form.middle_name|add_class:"form-control" }}
                                {% if form.middle_name.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.middle_name.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.birth_date.id_for_label }}" class="form-label">
                                    <strong>{{ form.birth_date.label }}</strong>
                                </label>
                                {{ form.birth_date|add_class:"form-control" }}
                                {% if form.birth_date.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.birth_date.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.gender.id_for_label }}" class="form-label">
                                    <strong>{{ form.gender.label }}</strong>
                                </label>
                                {{ form.gender|add_class:"form-select" }}
                                {% if form.gender.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.gender.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Контактная информация -->
                <div class="form-section">
                    <h5 class="section-title">
                        <i class="fas fa-phone me-2"></i>Контактная информация
                    </h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.phone.id_for_label }}" class="form-label">
                                    <strong>{{ form.phone.label }}</strong>
                                </label>
                                {{ form.phone|add_class:"form-control" }}
                                {% if form.phone.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.phone.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.email.id_for_label }}" class="form-label">
                                    <strong>{{ form.email.label }}</strong>
                                </label>
                                {{ form.email|add_class:"form-control" }}
                                {% if form.email.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.email.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Кнопки действий -->
                <div class="form-actions">
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <div class="btn-toolbar" role="toolbar" aria-label="Основные действия">
                            <div class="btn-group me-2" role="group">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save me-1"></i>Сохранить пациента
                                </button>
                            </div>
                            <div class="btn-group me-2" role="group">
                                <a href="{% url 'patients:patient_list' %}" 
                                   class="btn btn-outline-secondary">
                                    <i class="fas fa-times me-1"></i>Отмена
                                </a>
                            </div>
                        </div>
                        
                        <div class="ms-auto">
                            <a href="{% url 'patients:patient_list' %}" 
                               class="btn btn-secondary">
                                <i class="fas fa-arrow-left me-1"></i>К списку пациентов
                            </a>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### Форма записи на прием

```html
{% extends "patients/base.html" %}
{% load widget_tweaks %}

{% block title %}{{ title }} | МедКарт{% endblock %}

{% block content %}
<div class="form-container">
    <div class="card mt-4" style="z-index: 2;">
        <div class="card-body position-relative">
            <h4 class="card-title mb-4">{{ title }}</h4>
            
            <form method="post" class="appointment-form">
                {% csrf_token %}
                
                <!-- Информация о записи -->
                <div class="form-section">
                    <h5 class="section-title">
                        <i class="fas fa-calendar-check me-2"></i>Информация о записи
                    </h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.patient.id_for_label }}" class="form-label">
                                    <strong>{{ form.patient.label }}</strong>
                                </label>
                                {{ form.patient|add_class:"form-select" }}
                                {% if form.patient.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.patient.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.doctor.id_for_label }}" class="form-label">
                                    <strong>{{ form.doctor.label }}</strong>
                                </label>
                                {{ form.doctor|add_class:"form-select" }}
                                {% if form.doctor.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.doctor.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.date.id_for_label }}" class="form-label">
                                    <strong>{{ form.date.label }}</strong>
                                </label>
                                {{ form.date|add_class:"form-control" }}
                                {% if form.date.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.date.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="{{ form.time.id_for_label }}" class="form-label">
                                    <strong>{{ form.time.label }}</strong>
                                </label>
                                {{ form.time|add_class:"form-control" }}
                                {% if form.time.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.time.errors %}
                                            {{ error }}
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="{{ form.reason.id_for_label }}" class="form-label">
                            <strong>{{ form.reason.label }}</strong>
                        </label>
                        {{ form.reason|add_class:"form-control" }}
                        {% if form.reason.help_text %}
                            <small class="form-text text-muted">{{ form.reason.help_text }}</small>
                        {% endif %}
                        {% if form.reason.errors %}
                            <div class="invalid-feedback d-block">
                                {% for error in form.reason.errors %}
                                    {{ error }}
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                </div>

                <!-- Кнопки действий -->
                <div class="form-actions">
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <div class="btn-toolbar" role="toolbar" aria-label="Основные действия">
                            <div class="btn-group me-2" role="group">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-calendar-plus me-1"></i>Создать запись
                                </button>
                            </div>
                            <div class="btn-group me-2" role="group">
                                <a href="{% url 'appointments:calendar' %}" 
                                   class="btn btn-outline-secondary">
                                    <i class="fas fa-times me-1"></i>Отмена
                                </a>
                            </div>
                        </div>
                        
                        <div class="ms-auto">
                            <a href="{% url 'appointments:calendar' %}" 
                               class="btn btn-secondary">
                                <i class="fas fa-arrow-left me-1"></i>К календарю
                            </a>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

## JavaScript функциональность

```javascript
// Инициализация форм
document.addEventListener('DOMContentLoaded', function() {
    // Маски для полей
    const phoneMask = IMask(document.querySelector('input[name="phone"]'), {
        mask: '+{7}(000)000-00-00'
    });
    
    const dateMask = IMask(document.querySelector('input[name="birth_date"]'), {
        mask: Date,
        pattern: 'DD.MM.YYYY'
    });
    
    // Валидация форм
    const forms = document.querySelectorAll('.medical-form, .patient-form, .appointment-form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Анимации полей
    const formControls = document.querySelectorAll('.form-control, .form-select');
    formControls.forEach(control => {
        control.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        control.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
    
    // Автосохранение черновиков
    let autoSaveTimer;
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => {
                saveDraft(textarea.name, textarea.value);
            }, 2000);
        });
    });
});

// Функция сохранения черновика
function saveDraft(fieldName, value) {
    const draft = {
        field: fieldName,
        value: value,
        timestamp: new Date().toISOString()
    };
    
    localStorage.setItem(`draft_${fieldName}`, JSON.stringify(draft));
    
    // Показываем уведомление
    toastr.info('Черновик сохранен', {
        timeOut: 2000,
        positionClass: 'toast-top-right'
    });
}

// Функция восстановления черновика
function restoreDraft(fieldName) {
    const draft = localStorage.getItem(`draft_${fieldName}`);
    if (draft) {
        const data = JSON.parse(draft);
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field && !field.value) {
            field.value = data.value;
            toastr.info('Черновик восстановлен', {
                timeOut: 3000,
                positionClass: 'toast-top-right'
            });
        }
    }
}
```

## Дополнительные стили

```css
/* Анимации для полей */
.form-group.focused .form-label {
    color: var(--primary-color);
}

.form-group.focused .form-control {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}

/* Стили для select */
.form-select {
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23343a40' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m1 6 7 7 7-7'/%3e%3c/svg%3e");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    background-size: 16px 12px;
}

/* Стили для textarea */
textarea.form-control {
    min-height: 100px;
    resize: vertical;
}

/* Стили для чекбоксов и радио */
.form-check {
    margin-bottom: var(--spacing-sm);
}

.form-check-input:checked {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
}

.form-check-label {
    color: var(--text-primary);
    font-weight: 500;
}

/* Стили для файловых полей */
.form-control[type="file"] {
    padding: var(--spacing-sm);
}

.form-control[type="file"]::-webkit-file-upload-button {
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    margin-right: var(--spacing-sm);
    cursor: pointer;
    transition: all var(--transition-fast) ease;
}

.form-control[type="file"]::-webkit-file-upload-button:hover {
    background-color: var(--secondary-color);
}

/* Стили для полей с ошибками */
.form-control.is-invalid {
    border-color: var(--danger-color);
    box-shadow: 0 0 0 3px rgba(247, 37, 133, 0.1);
}

.form-control.is-valid {
    border-color: var(--success-color);
    box-shadow: 0 0 0 3px rgba(76, 201, 240, 0.1);
}

/* Стили для загрузки */
.form-loading {
    position: relative;
    pointer-events: none;
}

.form-loading::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.form-loading::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 20px;
    height: 20px;
    border: 2px solid var(--primary-color);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    z-index: 1001;
}

@keyframes spin {
    to {
        transform: translate(-50%, -50%) rotate(360deg);
    }
}
```

## Интеграция с Django

### Template tags

```python
# templatetags/form_tags.py
from django import template
from django.forms import BoundField

register = template.Library()

@register.simple_tag
def render_field(field, label_class='form-label', help_class='form-text'):
    """Рендерит поле формы с унифицированными стилями"""
    html = f'<div class="form-group">'
    
    # Label
    html += f'<label for="{field.id_for_label}" class="{label_class}">'
    html += f'<strong>{field.label}</strong></label>'
    
    # Field
    field_class = 'form-control'
    if field.field.widget.input_type == 'select':
        field_class = 'form-select'
    elif field.field.widget.input_type == 'checkbox':
        field_class = 'form-check-input'
    
    html += f'{field|add_class:field_class}'
    
    # Help text
    if field.help_text:
        html += f'<small class="{help_class}">{field.help_text}</small>'
    
    # Errors
    if field.errors:
        html += '<div class="invalid-feedback d-block">'
        for error in field.errors:
            html += f'{error}'
        html += '</div>'
    
    html += '</div>'
    return format_html(html)

@register.simple_tag
def render_form_section(title, icon='info-circle'):
    """Рендерит секцию формы"""
    html = f'<div class="form-section">'
    html += f'<h5 class="section-title">'
    html += f'<i class="fas fa-{icon} me-2"></i>{title}'
    html += f'</h5>'
    return format_html(html)
```

### Context processor

```python
# context_processors.py
def form_context(request):
    """Добавляет контекст для форм"""
    return {
        'FORM_DEFAULTS': {
            'cancel_url': request.META.get('HTTP_REFERER'),
            'back_url': request.META.get('HTTP_REFERER'),
        }
    }
```

## Тестирование

```python
# tests/test_forms.py
from django.test import TestCase, Client
from django.urls import reverse

class FormTestCase(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_form_rendering(self):
        """Тест рендеринга формы"""
        response = self.client.get(reverse('patients:patient_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form-container')
        self.assertContains(response, 'form-section')
        self.assertContains(response, 'btn-primary')
    
    def test_form_validation(self):
        """Тест валидации формы"""
        data = {
            'last_name': 'Иванов',
            'first_name': 'Иван',
            'birth_date': '01.01.1990',
        }
        response = self.client.post(reverse('patients:patient_create'), data)
        # Проверяем результат валидации
        self.assertEqual(response.status_code, 302)  # Редирект при успехе
```

---

**Дата создания**: 28.08.2025  
**Версия**: 2.0  
**Статус**: Активные компоненты  
**Основано на**: encounters/detail.html
