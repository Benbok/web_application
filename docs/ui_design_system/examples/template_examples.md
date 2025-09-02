# Примеры шаблонов - МедКарт

## Обзор

Данный документ содержит примеры шаблонов, основанные на существующих шаблонах приложения. Все примеры используют единую систему дизайна и color tokens для обеспечения консистентности.

## 1. Шаблон деталей плана обследования

### Описание
Шаблон для отображения детальной информации о плане обследования с прогрессом выполнения и списками исследований.

### HTML структура

```html
{% extends "patients/base.html" %}
{% load static %}

{% block title %}{{ examination_plan.name }}{% endblock %}

{% block content %}
<!-- Сообщения Django -->
{% if messages %}
<div class="messages mt-3">
  {% for message in messages %}
  <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
    {{ message }}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  </div>
  {% endfor %}
</div>
{% endif %}

<!-- Основная карточка плана обследования -->
<div class="card mt-4">
    <div class="card-header">
        <div class="d-flex justify-content-between align-items-center flex-wrap">
            <!-- Левая часть: Название и базовая информация -->
            <div>
                <h4 class="card-title mb-0">
                    <i class="fas fa-notes-medical"></i> {{ examination_plan.name }}
                </h4>
                <small class="text-muted">
                    {% if encounter.patient %}
                        Пациент: <a href="{% url 'patients:patient_detail' encounter.patient.pk %}">{{ encounter.patient.get_full_name_with_age }}</a> | 
                        Случай: <a href="{% url 'encounters:encounter_detail' encounter.id %}">{{ encounter.date_start|date:"d.m.Y" }}</a>
                    {% else %}
                        {{ encounter }}
                    {% endif %}
                </small>
            </div>
            
            <!-- Правая часть: Панель действий -->
            <div class="btn-toolbar mt-2 mt-md-0" role="toolbar">
                <div class="btn-group me-2" role="group">
                    <a href="{% url 'examination_management:lab_test_create' plan_pk=examination_plan.pk %}" class="btn btn-success">
                        <i class="fas fa-flask me-1"></i> Добавить лабораторное
                    </a>
                    <a href="{% url 'examination_management:instrumental_create' plan_pk=examination_plan.pk %}" class="btn btn-info">
                        <i class="fas fa-stethoscope me-1"></i> Добавить инструментальное
                    </a>
                </div>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                        Действия
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item text-danger" href="{% url 'examination_management:examination_plan_delete' encounter_pk=encounter.pk pk=examination_plan.pk %}">
                            <i class="fas fa-trash fa-fw me-2"></i>Удалить план
                        </a></li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card-body">
        <!-- Информационный блок -->
        <div class="mb-4">
            {% if examination_plan.description %}
                <div class="mb-3">
                    <h6 class="card-subtitle mb-2 text-muted">Описание:</h6>
                    <p class="mb-0">{{ examination_plan.description|linebreaks }}</p>
                </div>
            {% endif %}
            
            <!-- Блок прогресса выполнения плана -->
            {% if progress and progress.total > 0 %}
            <div class="mb-3">
                <h6 class="card-subtitle mb-2 text-muted">Прогресс выполнения:</h6>
                <div class="row">
                    <div class="col-md-8">
                        <div class="progress mb-2" style="height: 25px;">
                            <div class="progress-bar bg-success" role="progressbar" 
                                 style="width: {{ progress.percentage|default:0 }}%" 
                                 aria-valuenow="{{ progress.percentage|default:0 }}" 
                                 aria-valuemin="0" 
                                 aria-valuemax="100">
                                {{ progress.percentage|default:0 }}%
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="d-flex flex-column">
                            <small class="text-success">
                                <i class="fas fa-check-circle me-1"></i>Выполнено: {{ progress.completed|default:0 }}/{{ progress.total }}
                            </small>
                            {% if progress.rejected and progress.rejected > 0 %}
                            <small class="text-danger">
                                <i class="fas fa-times-circle me-1"></i>Забраковано: {{ progress.rejected }}
                            </small>
                            {% endif %}
                            {% if progress.active and progress.active > 0 %}
                            <small class="text-primary">
                                <i class="fas fa-clock me-1"></i>В работе: {{ progress.active }}
                            </small>
                            {% endif %}
                        </div>
                    </div>
                </div>
                
                <!-- Общий статус плана -->
                <div class="mt-2">
                    {% if progress.status == 'completed' %}
                        <span class="badge bg-success fs-6">
                            <i class="fas fa-check-circle me-1"></i>План полностью выполнен
                        </span>
                    {% elif progress.status == 'rejected' %}
                        <span class="badge bg-danger fs-6">
                            <i class="fas fa-times-circle me-1"></i>Все исследования забракованы
                        </span>
                    {% elif progress.status == 'in_progress' %}
                        <span class="badge bg-warning fs-6">
                            <i class="fas fa-clock me-1"></i>План в процессе выполнения
                        </span>
                    {% else %}
                        <span class="badge bg-secondary fs-6">
                            <i class="fas fa-hourglass-start me-1"></i>План ожидает выполнения
                        </span>
                    {% endif %}
                </div>
            </div>
            {% else %}
            <div class="mb-3">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>Прогресс выполнения:</strong> 
                    {% if progress %}
                        Всего исследований: {{ progress.total|default:0 }}, 
                        Выполнено: {{ progress.completed|default:0 }}, 
                        Забраковано: {{ progress.rejected|default:0 }}, 
                        В работе: {{ progress.active|default:0 }}
                    {% else %}
                        Данные прогресса недоступны
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <!-- Бейджи с метаинформацией -->
            <div class="d-flex flex-wrap gap-2">
                <span class="badge bg-light text-dark">
                    <i class="fas fa-clock me-1"></i>Создан: {{ examination_plan.created_at|date:"d.m.Y H:i" }}
                </span>
                <span class="badge bg-success text-white">
                    <i class="fas fa-flask me-1"></i>Лабораторных: {{ examination_plan.lab_tests.all.count }}
                </span>
                <span class="badge bg-info text-white">
                    <i class="fas fa-stethoscope me-1"></i>Инструментальных: {{ examination_plan.instrumental_procedures.all.count }}
                </span>
            </div>
        </div>
        
        <hr>

        <!-- Блок с лабораторными исследованиями -->
        <h5 class="mb-3"><i class="fas fa-flask me-1"></i> Лабораторные исследования</h5>
        {% if lab_tests_with_status %}
            <div class="row">
                {% for item in lab_tests_with_status %}
                {% with lab_test=item.examination_lab_test status_info=item.status_info %}
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100 {% if status_info.status == 'completed' %}border-success{% elif status_info.status == 'rejected' %}border-danger{% elif status_info.status == 'active' %}border-primary{% else %}border-secondary{% endif %}">
                        <div class="card-header bg-white p-3">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="flex-grow-1">
                                    <h6 class="mb-1">
                                        {% if status_info.status != 'active' and status_info.has_results %}
                                            <i class="fas fa-lock text-muted me-2" title="Исследование заблокировано для редактирования"></i>
                                        {% endif %}
                                        {{ lab_test.lab_test.name }}
                                    </h6>
                                    {% if lab_test.instructions %}
                                        <small class="text-muted">{{ lab_test.instructions|linebreaks }}</small>
                                    {% endif %}
                                </div>
                                <span class="badge {% if status_info.status == 'completed' %}bg-success{% elif status_info.status == 'rejected' %}bg-danger{% elif status_info.status == 'active' %}bg-primary{% else %}bg-secondary{% endif %} ms-2">
                                    {{ status_info.status_display }}
                                </span>
                            </div>
                        </div>
                        <div class="card-body d-flex flex-column">
                            {% if lab_test.instructions %}
                            <div class="mb-2">
                                <strong>Инструкции:</strong> {{ lab_test.instructions }}
                            </div>
                            {% endif %}
                            {% if lab_test.lab_test.description %}
                            <div class="mb-2">
                                <small class="text-muted">{{ lab_test.lab_test.description|truncatewords:15 }}</small>
                            </div>
                            {% endif %}
                            
                            <!-- Информация о статусе -->
                            <div class="mt-2">
                                {% if status_info.status == 'completed' %}
                                    <div class="alert alert-success py-2 mb-2">
                                        <small>
                                            <i class="fas fa-check-circle me-1"></i>
                                            <strong>Выполнено:</strong> {{ status_info.end_date|date:"d.m.Y H:i" }}
                                            {% if status_info.completed_by %}
                                                <br>Выполнил: {{ status_info.completed_by.doctor_profile.full_name|default:status_info.completed_by.get_full_name|default:status_info.completed_by.username }}
                                            {% endif %}
                                        </small>
                                    </div>
                                {% elif status_info.status == 'rejected' %}
                                    <div class="alert alert-danger py-2 mb-2">
                                        <small>
                                            <i class="fas fa-times-circle me-1"></i>
                                            <strong>Забраковано:</strong> {{ status_info.end_date|date:"d.m.Y H:i" }}
                                            {% if status_info.completed_by %}
                                                <br>Забраковал: {{ status_info.completed_by.doctor_profile.full_name|default:status_info.completed_by.get_full_name|default:status_info.completed_by.username }}
                                            {% endif %}
                                            {% if status_info.rejection_reason %}
                                                <br><strong>Причина:</strong> {{ status_info.rejection_reason|truncatechars:50 }}
                                            {% endif %}
                                        </small>
                                    </div>
                                {% elif status_info.status == 'active' %}
                                    <div class="alert alert-primary py-2 mb-2">
                                        <small>
                                            <i class="fas fa-clock me-1"></i>
                                            <strong>Ожидает выполнения</strong>
                                        </small>
                                    </div>
                                {% endif %}
                            </div>
                            
                            <div class="mt-auto">
                                <small class="text-muted">
                                    <i class="fas fa-calendar me-1"></i>Добавлено: {{ lab_test.created_at|date:"d.m.Y H:i" }}
                                </small>
                            </div>
                        </div>
                        <div class="card-footer bg-white p-2">
                            <div class="d-flex justify-content-end gap-2">
                                {% if status_info.status == 'completed' %}
                                    <a href="{% url 'examination_management:lab_test_result_view' pk=lab_test.pk %}" 
                                       class="btn btn-outline-info btn-sm"
                                       title="Просмотреть результат">
                                        <i class="fas fa-eye me-1"></i> Просмотреть результат
                                    </a>
                                {% elif lab_test.can_be_deleted %}
                                    <a href="{% url 'examination_management:lab_test_delete' pk=lab_test.pk %}" 
                                       class="btn btn-outline-danger btn-sm">
                                        <i class="fas fa-trash me-1"></i> Удалить
                                    </a>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endwith %}
                {% endfor %}
            </div>
        {% else %}
            <div class="text-center p-4 border rounded bg-light">
                <i class="fas fa-flask fa-2x text-muted mb-2"></i>
                <h6 class="text-muted">Лабораторные исследования пока не добавлены</h6>
                <p class="text-muted small">Начните, добавив первое лабораторное исследование в план обследования.</p>
                <a href="{% url 'examination_management:lab_test_create' plan_pk=examination_plan.pk %}" class="btn btn-success btn-sm">
                     <i class="fas fa-plus me-1"></i> Добавить лабораторное
                 </a>
            </div>
        {% endif %}
    </div>
</div>

<!-- Навигационные кнопки -->
<div class="d-flex gap-2 mt-4">
    <a href="{% url 'examination_management:examination_plan_list' encounter_pk=encounter.pk %}" class="btn btn-secondary">
        <i class="fas fa-arrow-left me-1"></i> Все планы обследования
    </a>
    <a href="{% url 'encounters:encounter_detail' pk=encounter.pk %}" class="btn btn-outline-secondary">
        <i class="fas fa-user me-1"></i> Вернуться к случаю
    </a>
</div>

{% endblock %}
```

### CSS стили

```css
/* Карточка плана обследования */
.card {
    border: none;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-sm);
    transition: all var(--transition-speed) ease;
}

.card:hover {
    box-shadow: var(--shadow-hover);
}

.card-header {
    background-color: var(--bg-secondary);
    border-bottom: 1px solid var(--border-light);
    padding: var(--spacing-lg);
}

.card-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
}

.card-title i {
    color: var(--primary-color);
}

/* Прогресс бар */
.progress {
    background-color: var(--bg-hover);
    border-radius: var(--border-radius);
    overflow: hidden;
}

.progress-bar {
    background-color: var(--success-color);
    transition: width var(--transition-speed) ease;
}

/* Бейджи */
.badge {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: var(--border-radius-sm);
}

.badge.bg-success {
    background-color: var(--success-color) !important;
}

.badge.bg-danger {
    background-color: var(--danger-color) !important;
}

.badge.bg-warning {
    background-color: var(--warning-color) !important;
}

.badge.bg-info {
    background-color: var(--info-color) !important;
}

.badge.bg-secondary {
    background-color: var(--text-muted) !important;
}

/* Карточки исследований */
.card.border-success {
    border-color: var(--success-color) !important;
}

.card.border-danger {
    border-color: var(--danger-color) !important;
}

.card.border-primary {
    border-color: var(--primary-color) !important;
}

.card.border-secondary {
    border-color: var(--border-color) !important;
}

/* Алерты */
.alert {
    border: none;
    border-radius: var(--border-radius);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
}

.alert-success {
    background-color: rgba(76, 201, 240, 0.1);
    color: var(--success-color);
    border-left: 3px solid var(--success-color);
}

.alert-danger {
    background-color: rgba(247, 37, 133, 0.1);
    color: var(--danger-color);
    border-left: 3px solid var(--danger-color);
}

.alert-primary {
    background-color: rgba(67, 97, 238, 0.1);
    color: var(--primary-color);
    border-left: 3px solid var(--primary-color);
}

.alert-info {
    background-color: rgba(67, 170, 139, 0.1);
    color: var(--info-color);
    border-left: 3px solid var(--info-color);
}

/* Пустое состояние */
.text-center.p-4.border.rounded.bg-light {
    background-color: var(--bg-primary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--border-radius) !important;
}

/* Кнопки */
.btn-toolbar {
    display: flex;
    gap: var(--spacing-sm);
}

.btn-group {
    display: flex;
    gap: var(--spacing-xs);
}

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

.btn-success {
    background-color: var(--success-color);
    border-color: var(--success-color);
    color: white;
}

.btn-info {
    background-color: var(--info-color);
    border-color: var(--info-color);
    color: white;
}

.btn-outline-danger {
    color: var(--danger-color);
    border-color: var(--danger-color);
    background-color: transparent;
}

.btn-outline-info {
    color: var(--info-color);
    border-color: var(--info-color);
    background-color: transparent;
}

/* Адаптивность */
@media (max-width: 768px) {
    .card-header .d-flex {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .btn-toolbar {
        margin-top: var(--spacing-md);
        width: 100%;
        justify-content: flex-start;
    }
    
    .btn-group {
        flex-wrap: wrap;
    }
}
```

## 2. Шаблон подтверждения удаления

### Описание
Шаблон для подтверждения удаления/отмены плана обследования с предупреждением и информацией о последствиях.

### HTML структура

```html
{% extends 'patients/base.html' %}
{% load static %}

{% block title %}Отменить план обследования{% endblock %}

{% block page_title %}Отменить план обследования{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0 text-warning">
                        <i class="fas fa-exclamation-triangle me-1"></i> Подтверждение отмены
                    </h5>
                </div>
                <div class="card-body">
                    <p class="card-text">
                        Вы действительно хотите <strong>отменить</strong> план обследования <strong>"{{ object.name }}"</strong>?
                    </p>
                    
                    <div class="alert alert-info">
                        <h6><i class="fas fa-info-circle"></i> Что происходит при отмене:</h6>
                        <ul class="mb-0">
                            <li>План обследования помечается как "Отменено"</li>
                            <li>Все лабораторные исследования в плане отменяются</li>
                            <li>Все инструментальные исследования в плане отменяются</li>
                            <li>Сохраняется полная история всех исследований</li>
                            <li>Автоматически отменяются все запланированные события</li>
                            <li>Все записи остаются в базе данных для аудита</li>
                        </ul>
                    </div>
                    
                    <p class="card-text text-muted">
                        <strong>Это действие можно отменить, возобновив план обследования!</strong>
                    </p>
                    
                    <form method="post">
                        {% csrf_token %}
                        <div class="d-flex justify-content-between">
                            <a href="{% url 'examination_management:examination_plan_detail' encounter_pk=object.encounter.pk pk=object.pk %}" 
                               class="btn btn-secondary">
                                <i class="fas fa-times me-1"></i> Отмена
                            </a>
                            <button type="submit" class="btn btn-warning">
                                <i class="fas fa-ban me-1"></i> Отменить план
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### CSS стили

```css
/* Контейнер подтверждения */
.container {
    max-width: 600px;
    margin: 0 auto;
}

/* Карточка подтверждения */
.card {
    border: none;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-md);
    transition: all var(--transition-speed) ease;
}

.card:hover {
    box-shadow: var(--shadow-lg);
}

.card-header {
    background-color: var(--bg-secondary);
    border-bottom: 1px solid var(--border-light);
    border-radius: var(--border-radius) var(--border-radius) 0 0;
    padding: var(--spacing-lg);
}

.card-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: center;
}

.card-title.text-warning {
    color: var(--warning-color) !important;
}

.card-title i {
    color: var(--warning-color);
}

.card-body {
    padding: var(--spacing-lg);
}

/* Текст подтверждения */
.card-text {
    font-size: 1rem;
    line-height: 1.6;
    color: var(--text-primary);
    margin-bottom: var(--spacing-lg);
}

.card-text strong {
    color: var(--text-primary);
    font-weight: 600;
}

.card-text.text-muted {
    color: var(--text-muted);
    font-size: 0.9rem;
}

/* Информационный блок */
.alert-info {
    background-color: rgba(67, 170, 139, 0.1);
    color: var(--info-color);
    border: none;
    border-left: 3px solid var(--info-color);
    border-radius: var(--border-radius);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
}

.alert-info h6 {
    color: var(--info-color);
    font-weight: 600;
    margin-bottom: var(--spacing-sm);
    display: flex;
    align-items: center;
}

.alert-info h6 i {
    margin-right: var(--spacing-xs);
}

.alert-info ul {
    margin: 0;
    padding-left: var(--spacing-lg);
}

.alert-info li {
    margin-bottom: var(--spacing-xs);
    color: var(--text-primary);
}

.alert-info li:last-child {
    margin-bottom: 0;
}

/* Форма действий */
form {
    margin-top: var(--spacing-lg);
}

.d-flex.justify-content-between {
    gap: var(--spacing-md);
}

/* Кнопки */
.btn {
    border-radius: var(--border-radius);
    padding: var(--spacing-sm) var(--spacing-lg);
    font-size: 0.9rem;
    font-weight: 500;
    transition: all var(--transition-fast) ease;
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    min-width: 120px;
    justify-content: center;
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

.btn-warning {
    background-color: var(--warning-color);
    border-color: var(--warning-color);
    color: white;
}

.btn-warning:hover {
    background-color: #e08516;
    border-color: #e08516;
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

/* Адаптивность */
@media (max-width: 768px) {
    .container {
        padding: 0 var(--spacing-md);
    }
    
    .d-flex.justify-content-between {
        flex-direction: column;
        gap: var(--spacing-sm);
    }
    
    .btn {
        width: 100%;
        justify-content: center;
    }
}
```

## 3. Общие паттерны

### Цветовая схема
Все шаблоны используют единую цветовую схему:

```css
:root {
  --primary-color: #4361ee;    /* Основной синий */
  --success-color: #4cc9f0;    /* Голубой для успеха */
  --danger-color: #f72585;     /* Розовый для опасности */
  --warning-color: #f8961e;    /* Оранжевый для предупреждений */
  --info-color: #43aa8b;       /* Зеленый для информации */
}
```

### Структурные элементы
- **Карточки** с тенями и скругленными углами
- **Бейджи** для статусов и метаинформации
- **Прогресс-бары** для отображения выполнения
- **Алерты** для уведомлений и предупреждений
- **Кнопки** с иконками и состояниями

### Адаптивность
Все шаблоны адаптированы для мобильных устройств:
- Гибкая сетка с использованием Bootstrap
- Адаптивные кнопки и навигация
- Оптимизированные размеры для сенсорных экранов

### Доступность
- Семантические HTML элементы
- ARIA-атрибуты для интерактивных элементов
- Контрастные цвета для лучшей читаемости
- Поддержка клавиатурной навигации

---

**Дата создания**: 28.08.2025  
**Версия**: 2.0  
**Статус**: Активные примеры  
**Основано на**: examination_management шаблонах
