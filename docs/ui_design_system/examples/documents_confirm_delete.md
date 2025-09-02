# Шаблон подтверждения удаления документов - МедКарт

## Обзор

Обновленный шаблон подтверждения удаления документов, созданный в соответствии с системой дизайна МедКарт. Шаблон обеспечивает четкое предупреждение пользователя о необратимости действия и предоставляет подробную информацию о документе.

## Файлы

- **HTML**: `base/documents/templates/documents/confirm_delete.html`
- **CSS**: `base/documents/static/documents/css/confirm_delete.css`

## HTML структура

```html
{% extends "patients/base.html" %}
{% load static %}

{% block title %}{{ title }}{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'documents/css/confirm_delete.css' %}">
{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0 text-danger">
                        <i class="fas fa-exclamation-triangle me-1"></i> Подтверждение удаления
                    </h5>
                </div>
                <div class="card-body">
                    <p class="card-text">
                        Вы действительно хотите <strong>удалить</strong> документ <strong>"{{ document.document_type.name }}"</strong> от <strong>{{ document.datetime_document|date:"d.m.Y H:i" }}</strong>?
                    </p>
                    
                    <div class="alert alert-warning">
                        <h6><i class="fas fa-exclamation-triangle"></i> Внимание:</h6>
                        <ul class="mb-0">
                            <li>Документ будет безвозвратно удален из системы</li>
                            <li>Все связанные данные будут потеряны</li>
                            <li>Это действие нельзя отменить</li>
                            <li>Рекомендуется создать резервную копию перед удалением</li>
                        </ul>
                    </div>
                    
                    <div class="alert alert-info">
                        <h6><i class="fas fa-info-circle"></i> Информация о документе:</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <small><strong>Тип документа:</strong><br>{{ document.document_type.name }}</small>
                            </div>
                            <div class="col-md-6">
                                <small><strong>Дата создания:</strong><br>{{ document.datetime_document|date:"d.m.Y H:i" }}</small>
                            </div>
                        </div>
                        {% if document.patient %}
                        <div class="mt-2">
                            <small><strong>Пациент:</strong> {{ document.patient.get_full_name_with_age }}</small>
                        </div>
                        {% endif %}
                    </div>
                    
                    <p class="card-text text-muted">
                        <strong>Это действие является необратимым!</strong>
                    </p>
                    
                    <form method="post">
                        {% csrf_token %}
                        <div class="d-flex justify-content-between">
                            <a href="{{ request.GET.next|default:'/' }}" class="btn btn-secondary">
                                <i class="fas fa-times me-1"></i> Отмена
                            </a>
                            <button type="submit" class="btn btn-danger">
                                <i class="fas fa-trash me-1"></i> Удалить документ
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

## CSS стили

```css
/* Стили для шаблона подтверждения удаления документов - МедКарт */

/* Карточка на всю ширину страницы */
.card {
    width: 100%;
    margin: 0;
}

/* Карточка подтверждения */
.card {
    border: none;
    border-radius: var(--border-radius, 8px);
    box-shadow: var(--shadow-md, 0 5px 20px rgba(0, 0, 0, 0.1));
    transition: all var(--transition-speed, 0.3s) ease;
}

.card:hover {
    box-shadow: var(--shadow-lg, 0 10px 30px rgba(0, 0, 0, 0.15));
}

.card-header {
    background-color: var(--bg-secondary, #ffffff);
    border-bottom: 1px solid var(--border-light, #eeeeee);
    border-radius: var(--border-radius, 8px) var(--border-radius, 8px) 0 0;
    padding: var(--spacing-lg, 24px);
}

.card-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: center;
}

.card-title.text-danger {
    color: var(--danger-color, #f72585) !important;
}

.card-title i {
    color: var(--danger-color, #f72585);
}

.card-body {
    padding: var(--spacing-lg, 24px);
}

/* Текст подтверждения */
.card-text {
    font-size: 1rem;
    line-height: 1.6;
    color: var(--text-primary, #333333);
    margin-bottom: var(--spacing-lg, 24px);
}

.card-text strong {
    color: var(--text-primary, #333333);
    font-weight: 600;
}

.card-text.text-muted {
    color: var(--text-muted, #777777);
    font-size: 0.9rem;
}

/* Предупреждающий блок */
.alert-warning {
    background-color: rgba(248, 150, 30, 0.1);
    color: var(--warning-color, #f8961e);
    border: none;
    border-left: 3px solid var(--warning-color, #f8961e);
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-md, 16px);
    margin-bottom: var(--spacing-lg, 24px);
}

.alert-warning h6 {
    color: var(--warning-color, #f8961e);
    font-weight: 600;
    margin-bottom: var(--spacing-sm, 8px);
    display: flex;
    align-items: center;
}

.alert-warning h6 i {
    margin-right: var(--spacing-xs, 4px);
}

.alert-warning ul {
    margin: 0;
    padding-left: var(--spacing-lg, 24px);
}

.alert-warning li {
    margin-bottom: var(--spacing-xs, 4px);
    color: var(--text-primary, #333333);
}

.alert-warning li:last-child {
    margin-bottom: 0;
}

/* Информационный блок */
.alert-info {
    background-color: rgba(67, 170, 139, 0.1);
    color: var(--info-color, #43aa8b);
    border: none;
    border-left: 3px solid var(--info-color, #43aa8b);
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-md, 16px);
    margin-bottom: var(--spacing-lg, 24px);
}

.alert-info h6 {
    color: var(--info-color, #43aa8b);
    font-weight: 600;
    margin-bottom: var(--spacing-sm, 8px);
    display: flex;
    align-items: center;
}

.alert-info h6 i {
    margin-right: var(--spacing-xs, 4px);
}

.alert-info .row {
    margin: 0;
}

.alert-info .col-md-6 {
    padding: 0 var(--spacing-sm, 8px);
}

.alert-info small {
    color: var(--text-primary, #333333);
    line-height: 1.4;
}

.alert-info small strong {
    color: var(--text-primary, #333333);
    font-weight: 600;
}

/* Форма действий */
form {
    margin-top: var(--spacing-lg, 24px);
}

.d-flex.justify-content-between {
    gap: var(--spacing-md, 16px);
}

/* Кнопки */
.btn {
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-sm, 8px) var(--spacing-lg, 24px);
    font-size: 0.9rem;
    font-weight: 500;
    transition: all var(--transition-fast, 0.2s) ease;
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs, 4px);
    min-width: 120px;
    justify-content: center;
}

.btn-secondary {
    background-color: var(--text-secondary, #555555);
    border-color: var(--text-secondary, #555555);
    color: white;
}

.btn-secondary:hover {
    background-color: var(--text-primary, #333333);
    border-color: var(--text-primary, #333333);
    transform: translateY(-1px);
}

.btn-danger {
    background-color: var(--danger-color, #f72585);
    border-color: var(--danger-color, #f72585);
    color: white;
}

.btn-danger:hover {
    background-color: #e01e6f;
    border-color: #e01e6f;
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm, 0 2px 10px rgba(0, 0, 0, 0.05));
}

/* Адаптивность */
@media (max-width: 768px) {
    .d-flex.justify-content-between {
        flex-direction: column;
        gap: var(--spacing-sm, 8px);
    }
    
    .btn {
        width: 100%;
        justify-content: center;
    }
    
    .alert-info .row {
        flex-direction: column;
    }
    
    .alert-info .col-md-6 {
        margin-bottom: var(--spacing-sm, 8px);
    }
    
    .alert-info .col-md-6:last-child {
        margin-bottom: 0;
    }
}

/* Анимации */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.card {
    animation: fadeIn 0.3s ease-out;
}

/* Фокус для доступности */
.btn:focus {
    outline: 2px solid var(--primary-color, #4361ee);
    outline-offset: 2px;
}

.alert:focus-within {
    outline: 2px solid var(--primary-color, #4361ee);
    outline-offset: 2px;
}
```

## Ключевые особенности

### 1. Структура и компоновка
- **Карточка на всю ширину страницы** для максимального использования пространства
- **Четкое разделение** на заголовок, контент и действия
- **Адаптивная сетка** для мобильных устройств

### 2. Цветовая схема
- **Красный заголовок** (`#f72585`) для предупреждения об опасности
- **Оранжевый алерт** (`#f8961e`) для предупреждений
- **Зеленый алерт** (`#43aa8b`) для информации
- **Серые кнопки** для вторичных действий

### 3. Информационные блоки
- **Предупреждающий блок** с последствиями удаления
- **Информационный блок** с деталями документа
- **Четкое разделение** между предупреждением и информацией

### 4. Интерактивность
- **Hover эффекты** на карточке и кнопках
- **Анимация появления** карточки
- **Трансформации** кнопок при наведении

### 5. Доступность
- **Семантические HTML элементы**
- **ARIA-атрибуты** для интерактивных элементов
- **Фокус-индикаторы** для клавиатурной навигации
- **Контрастные цвета** для лучшей читаемости

## Использование

### Для разработчиков
1. **Подключите CSS файл** в шаблоне через `{% block extra_css %}`
2. **Используйте структуру** как основу для других форм подтверждения
3. **Адаптируйте контент** под конкретные потребности
4. **Тестируйте** на различных устройствах

### Для дизайнеров
1. **Следуйте цветовой схеме** из design tokens
2. **Используйте иконки Font Awesome** для консистентности
3. **Поддерживайте адаптивность** для мобильных устройств
4. **Проверяйте доступность** по стандартам WCAG

## Преимущества

### Консистентность
- Единая цветовая палитра с системой дизайна
- Стандартизированные компоненты и паттерны
- Последовательное использование типографики

### Пользовательский опыт
- Четкое предупреждение о последствиях
- Подробная информация о документе
- Интуитивно понятные действия

### Безопасность
- Множественные предупреждения о необратимости
- Рекомендации по резервному копированию
- Четкое разделение между отменой и удалением

---

**Дата создания**: 28.08.2025  
**Версия**: 2.0  
**Статус**: Активный шаблон  
**Основано на**: Системе дизайна МедКарт
