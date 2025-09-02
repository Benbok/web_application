# Руководство по использованию MCP Context7

**Версия документа:** 1.0  
**Дата создания:** 28.08.2025  
**Статус:** Активное руководство

## Обзор

MCP Context7 - это сервер для получения актуальной документации по библиотекам и технологиям. Интеграция с проектом МедКарт обеспечивает доступ к свежей документации и лучшим практикам.

## Основные возможности

### 1. Поиск библиотек
```python
# Поиск библиотеки по названию
resolve-library-id: django
resolve-library-id: djangorestframework
resolve-library-id: psycopg2
```

### 2. Получение документации
```python
# Получение документации по конкретной библиотеке
get-library-docs: /django/django
get-library-docs: /encode/django-rest-framework
get-library-docs: /psycopg/psycopg2
```

### 3. Фокусировка на темах
```python
# Получение документации по конкретной теме
get-library-docs: /django/django, topic: models
get-library-docs: /encode/django-rest-framework, topic: serializers
```

## Библиотеки проекта МедКарт

### Backend библиотеки

#### Django 5.2.4
- **ID:** `/django/django`
- **Использование:** Основной веб-фреймворк
- **Ключевые темы:**
  - Models и ORM
  - Views и контроллеры
  - Forms и валидация
  - Templates
  - Middleware
  - Security

#### Django REST Framework
- **ID:** `/encode/django-rest-framework`
- **Использование:** Создание REST API
- **Ключевые темы:**
  - Serializers
  - ViewSets
  - Authentication
  - Permissions
  - Pagination
  - Filtering

#### PostgreSQL (psycopg2)
- **ID:** `/psycopg/psycopg2`
- **Использование:** База данных
- **Ключевые темы:**
  - Connection management
  - Query optimization
  - Transactions
  - Indexing

#### Redis
- **ID:** `/redis/redis-py`
- **Использование:** Кеширование
- **Ключевые темы:**
  - Caching strategies
  - Session storage
  - Pub/Sub
  - Data structures

### Frontend библиотеки

#### Bootstrap 5
- **ID:** `/twbs/bootstrap`
- **Использование:** CSS фреймворк
- **Ключевые темы:**
  - Grid system
  - Components
  - Utilities
  - Responsive design

#### jQuery (при необходимости)
- **ID:** `/jquery/jquery`
- **Использование:** JavaScript библиотека
- **Ключевые темы:**
  - DOM manipulation
  - AJAX
  - Events
  - Animations

### Утилиты и инструменты

#### Pandas
- **ID:** `/pandas-dev/pandas`
- **Использование:** Анализ данных
- **Ключевые темы:**
  - Data manipulation
  - Analysis
  - Visualization
  - Performance

#### Pillow
- **ID:** `/python-pillow/Pillow`
- **Использование:** Обработка изображений
- **Ключевые темы:**
  - Image processing
  - Formats
  - Filters
  - Optimization

#### Pytest
- **ID:** `/pytest-dev/pytest`
- **Использование:** Тестирование
- **Ключевые темы:**
  - Test writing
  - Fixtures
  - Coverage
  - Plugins

## Рабочий процесс с MCP Context7

### При разработке новых функций

#### 1. Определение используемых библиотек
```python
# Пример: создание новой модели пациента
# resolve-library-id: django
# get-library-docs: /django/django, topic: models
```

#### 2. Получение лучших практик
```python
# Пример: создание API endpoint
# resolve-library-id: djangorestframework
# get-library-docs: /encode/django-rest-framework, topic: viewsets
```

#### 3. Применение в коде
```python
# Применение полученных знаний
from django.db import models
from rest_framework import viewsets

class Patient(models.Model):
    # Использование лучших практик Django Models
    pass

class PatientViewSet(viewsets.ModelViewSet):
    # Использование лучших практик DRF ViewSets
    pass
```

### При решении проблем

#### 1. Идентификация проблемы
```python
# Проблема: медленные запросы к базе данных
# resolve-library-id: django
# get-library-docs: /django/django, topic: database optimization
```

#### 2. Поиск решения
```python
# Поиск решения для оптимизации
# resolve-library-id: psycopg2
# get-library-docs: /psycopg/psycopg2, topic: performance
```

#### 3. Применение решения
```python
# Применение оптимизации
queryset = Patient.objects.select_related('department').prefetch_related('encounters')
```

### При обновлении зависимостей

#### 1. Проверка изменений
```python
# Проверка изменений в новой версии Django
# resolve-library-id: django
# get-library-docs: /django/django, topic: release notes
```

#### 2. Изучение breaking changes
```python
# Изучение breaking changes
# get-library-docs: /django/django, topic: migration guide
```

#### 3. Обновление кода
```python
# Обновление кода согласно новым требованиям
# Применение новых best practices
```

## Примеры использования

### Создание модели пациента

```python
# Получение документации по Django Models
# resolve-library-id: django
# get-library-docs: /django/django, topic: models

from django.db import models
from django.core.validators import RegexValidator

class Patient(models.Model):
    """
    Модель пациента с использованием лучших практик Django
    """
    # Использование TextChoices для выбора
    class Gender(models.TextChoices):
        MALE = 'male', 'Мужской'
        FEMALE = 'female', 'Женский'
        OTHER = 'other', 'Другой'
    
    # Валидация данных
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+999999999'"
    )
    
    # Поля модели
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    birth_date = models.DateField("Дата рождения")
    gender = models.CharField("Пол", max_length=10, choices=Gender.choices)
    phone = models.CharField("Телефон", validators=[phone_regex], max_length=17)
    
    class Meta:
        verbose_name = "Пациент"
        verbose_name_plural = "Пациенты"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['birth_date']),
        ]
    
    def __str__(self):
        return f"{self.last_name} {self.first_name}"
```

### Создание API endpoint

```python
# Получение документации по DRF
# resolve-library-id: djangorestframework
# get-library-docs: /encode/django-rest-framework, topic: viewsets

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с пациентами
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Оптимизация запросов
    def get_queryset(self):
        return Patient.objects.select_related('department').prefetch_related('encounters')
    
    # Кастомные действия
    @action(detail=True, methods=['get'])
    def encounters(self, request, pk=None):
        """Получить все встречи пациента"""
        patient = self.get_object()
        encounters = patient.encounters.all()
        serializer = EncounterSerializer(encounters, many=True)
        return Response(serializer.data)
```

### Оптимизация запросов

```python
# Получение документации по оптимизации
# resolve-library-id: django
# get-library-docs: /django/django, topic: database optimization

# Плохой запрос
patients = Patient.objects.all()
for patient in patients:
    print(patient.department.name)  # N+1 проблема

# Хороший запрос
patients = Patient.objects.select_related('department').all()
for patient in patients:
    print(patient.department.name)  # Оптимизировано
```

## Лучшие практики

### 1. Регулярное обновление знаний
- Получайте документацию перед началом работы с новой библиотекой
- Изучайте breaking changes при обновлении версий
- Следите за новыми best practices

### 2. Документирование решений
- Записывайте полученные знания в проектную документацию
- Создавайте примеры использования для команды
- Обновляйте внутренние руководства

### 3. Обучение команды
- Проводите регулярные сессии по изучению новых возможностей
- Делитесь полученными знаниями с коллегами
- Создавайте внутреннюю базу знаний

### 4. Интеграция в процесс разработки
- Используйте MCP Context7 при code review
- Получайте документацию при решении проблем
- Изучайте альтернативные подходы

## Troubleshooting

### Проблемы с поиском библиотек
```python
# Если библиотека не найдена, попробуйте альтернативные названия
resolve-library-id: django-rest-framework  # Вместо djangorestframework
resolve-library-id: postgresql  # Вместо psycopg2
```

### Проблемы с получением документации
```python
# Укажите конкретную тему для более точных результатов
get-library-docs: /django/django, topic: models, tokens: 5000
```

### Проблемы с актуальностью
```python
# Получите документацию по конкретной версии
get-library-docs: /django/django/v5.2.4, topic: models
```

## Заключение

MCP Context7 значительно улучшает качество разработки, обеспечивая доступ к актуальной документации и лучшим практикам. Регулярное использование этого инструмента поможет команде создавать более качественный и современный код.

---

**Документ подготовлен:** Системный архитектор  
**Дата создания:** 28.08.2025  
**Последнее обновление:** 28.08.2025
