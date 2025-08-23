# 📝 Система подписей документов (Document Signatures)

Универсальное Django-приложение для управления электронными подписями документов в медицинской информационной системе.

## 🎯 Основные возможности

### ✅ Автоматическое создание подписей
- При создании результатов исследований автоматически создаются необходимые подписи
- Настраиваемые рабочие процессы для разных типов документов
- Шаблоны для быстрого применения процессов

### 🔐 Многоуровневая система подписей
- **Врач-исследователь** - основная подпись
- **Заведующий отделением** - контроль качества
- **Главный врач** - для сложных случаев
- **Пациент** - согласие с результатами (опционально)

### 🚀 Интеграция с существующими приложениями
- `examination_management` - планы обследования
- `instrumental_procedures` - инструментальные исследования
- `lab_tests` - лабораторные исследования
- `treatment_management` - планы лечения
- `prescriptions` - рецепты

## 🏗️ Архитектура

### Модели
- **`SignatureWorkflow`** - рабочие процессы подписей
- **`DocumentSignature`** - отдельные подписи документов
- **`SignatureTemplate`** - шаблоны для быстрого применения

### Сервисы
- **`SignatureService`** - основная бизнес-логика
- Автоматическое создание подписей
- Управление статусами
- Проверка прав доступа

### Сигналы
- Автоматическая интеграция с другими приложениями
- Синхронизация статусов
- Обновление `examination_management` и `clinical_scheduling`

## 🚀 Быстрый старт

### 1. Установка

Приложение уже добавлено в `INSTALLED_APPS` и настроено в URL-маршрутах.

### 2. Создание миграций

```bash
python manage.py makemigrations document_signatures
python manage.py migrate
```

### 3. Тестирование

```bash
python manage.py test_signatures
```

### 4. Доступ к интерфейсу

- **Список подписей:** `/signatures/`
- **Дашборд:** `/signatures/dashboard/`
- **Рабочие процессы:** `/signatures/workflows/`
- **Шаблоны:** `/signatures/templates/`

## 📋 Использование в шаблонах

### Загрузка тегов

```html
{% load signature_tags %}
```

### Отображение статуса подписей

```html
{% get_signature_status result as signature_status %}
<span class="badge bg-{{ signature_status.color }}">
    {{ signature_status.text }}
</span>
```

### Прогресс-бар подписей

```html
{% get_signature_progress_bar result as progress_html %}
{{ progress_html|safe }}
```

### Проверка возможности подписи

```html
{% can_user_sign_document result request.user as can_sign %}
{% if can_sign %}
    <a href="{% url 'document_signatures:signature_list' %}" class="btn btn-primary">
        <i class="fas fa-signature"></i> Подписать
    </a>
{% endif %}
```

### Ссылка на подписи документа

```html
{% get_signature_link result as signature_url %}
<a href="{{ signature_url }}">Просмотр подписей</a>
```

## 🔧 Настройка рабочих процессов

### Простая подпись (только врач)
```python
workflow = SignatureWorkflow.objects.create(
    name='Простая подпись',
    workflow_type='simple',
    require_doctor_signature=True,
    auto_complete_on_doctor_signature=True
)
```

### Стандартная подпись (врач + заведующий)
```python
workflow = SignatureWorkflow.objects.create(
    name='Стандартная подпись',
    workflow_type='standard',
    require_doctor_signature=True,
    require_head_signature=True,
    auto_complete_on_all_signatures=True
)
```

### Сложная подпись (врач + заведующий + главный врач)
```python
workflow = SignatureWorkflow.objects.create(
    name='Сложная подпись',
    workflow_type='complex',
    require_doctor_signature=True,
    require_head_signature=True,
    require_chief_signature=True,
    auto_complete_on_all_signatures=True
)
```

## 🔌 API для разработчиков

### Создание подписей для документа

```python
from document_signatures.services import SignatureService

# Автоматическое создание с типом процесса
signatures = SignatureService.create_signatures_for_document(
    document=lab_test_result,
    workflow_type='simple'
)

# Создание с пользовательским процессом
signatures = SignatureService.create_signatures_for_document(
    document=lab_test_result,
    custom_workflow=my_workflow
)
```

### Подписание документа

```python
# Подписание с комментариями
SignatureService.sign_document(
    signature_id=signature.pk,
    user=request.user,
    notes='Результат проверен и подтвержден'
)
```

### Проверка статуса

```python
# Проверка завершения
is_completed = SignatureService.check_document_completion(document)

# Получение детального статуса
status = SignatureService.get_document_signature_status(document)
print(f"Прогресс: {status['progress']}%")
print(f"Текст: {status['text']}")
print(f"Цвет: {status['color']}")
```

## 🎨 Кастомизация

### Добавление новых типов подписей

1. Обновите `SIGNATURE_TYPES` в модели `DocumentSignature`
2. Добавьте логику в метод `can_sign`
3. Обновите шаблоны и формы

### Создание новых рабочих процессов

1. Создайте экземпляр `SignatureWorkflow`
2. Настройте требуемые подписи
3. Установите таймауты и автоматические действия

### Интеграция с новыми приложениями

1. Добавьте сигнал в `signals.py`
2. Используйте `SignatureService.create_signatures_for_document`
3. Обновите шаблоны для отображения статуса

## 🔒 Права доступа

### Основные права
- `document_signatures.add_signatureworkflow` - создание рабочих процессов
- `document_signatures.change_signatureworkflow` - редактирование процессов
- `document_signatures.can_sign_as_head` - подпись как заведующий
- `document_signatures.can_sign_as_chief` - подпись как главный врач
- `document_signatures.can_reject_signature` - отклонение подписей
- `document_signatures.can_cancel_signature` - отмена подписей

### Настройка прав

```python
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# Создание права для заведующего отделением
content_type = ContentType.objects.get_for_app_label('document_signatures')
permission = Permission.objects.create(
    codename='can_sign_as_head',
    name='Can sign as head of department',
    content_type=content_type,
)
```

## 📊 Мониторинг и статистика

### Дашборд подписей
- Общая статистика по подписям
- Статистика по пользователям
- Анализ по типам и статусам

### Отчеты
- Подписи по периодам
- Анализ эффективности процессов
- Выявление узких мест

## 🚨 Устранение неполадок

### Ошибка "Документ не найден"
- Проверьте, что модель документа существует
- Убедитесь, что `content_type` корректно определен

### Подписи не создаются автоматически
- Проверьте, что сигналы зарегистрированы
- Убедитесь, что `SignatureService` доступен
- Проверьте логи на наличие ошибок

### Пользователь не может подписать
- Проверьте права доступа
- Убедитесь, что подпись в статусе 'pending'
- Проверьте, не истек ли срок подписи

## 🔮 Планы развития

### Краткосрочные
- [ ] Уведомления о необходимости подписи
- [ ] Мобильный интерфейс для подписей
- [ ] Экспорт подписей в PDF

### Долгосрочные
- [ ] Цифровые подписи с криптографией
- [ ] Интеграция с внешними системами
- [ ] Машинное обучение для оптимизации процессов

## 📞 Поддержка

При возникновении вопросов или проблем:
1. Проверьте логи Django
2. Убедитесь, что все зависимости установлены
3. Проверьте корректность настроек
4. Обратитесь к документации Django

---

**🎯 Система подписей готова к использованию в production!** 