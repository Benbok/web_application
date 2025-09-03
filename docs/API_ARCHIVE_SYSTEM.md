# API системы архивирования

## Обзор

API системы архивирования предоставляет RESTful интерфейс для управления архивированием записей в медицинской информационной системе "МедКарта". API построен на основе Django REST Framework и поддерживает все основные операции архивирования.

## Аутентификация

API использует стандартную аутентификацию Django. Все запросы должны быть авторизованы.

### Методы аутентификации:
- Session Authentication (для веб-интерфейса)
- Token Authentication (для мобильных приложений)
- Basic Authentication (для тестирования)

## Базовый URL

```
/api/v1/
```

## Эндпоинты

### 1. Логи архивирования

#### Получение списка логов
```
GET /api/v1/archive-logs/
```

**Параметры запроса:**
- `action` - фильтр по действию (archive/restore)
- `user` - ID пользователя
- `model` - название модели
- `app` - название приложения
- `since` - дата начала (YYYY-MM-DD)
- `until` - дата окончания (YYYY-MM-DD)
- `page` - номер страницы
- `page_size` - размер страницы (максимум 100)

**Пример ответа:**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/v1/archive-logs/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "action": "archive",
            "content_type": {
                "id": 1,
                "app_label": "patients",
                "model": "patient",
                "name": "Patient"
            },
            "object_id": 123,
            "user": {
                "id": 1,
                "username": "doctor_smith",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "email": "john.smith@hospital.com"
            },
            "timestamp": "2024-01-15T10:30:00Z",
            "reason": "Пациент выписан",
            "metadata": {
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0..."
            }
        }
    ]
}
```

#### Статистика архивирования
```
GET /api/v1/archive-logs/statistics/
```

**Пример ответа:**
```json
{
    "total_logs": 150,
    "archive_count": 120,
    "restore_count": 30,
    "model_statistics": [
        {
            "content_type__app_label": "patients",
            "content_type__model": "patient",
            "archive_count": 50,
            "restore_count": 10
        }
    ],
    "top_users": [
        {
            "user__username": "doctor_smith",
            "user__first_name": "John",
            "user__last_name": "Smith",
            "total_actions": 25
        }
    ]
}
```

### 2. Конфигурация архивирования

#### Получение списка конфигураций
```
GET /api/v1/archive-configurations/
```

**Параметры запроса:**
- `app` - фильтр по приложению
- `model` - фильтр по модели

**Пример ответа:**
```json
[
    {
        "id": 1,
        "content_type": {
            "id": 1,
            "app_label": "patients",
            "model": "patient",
            "name": "Patient"
        },
        "is_archivable": true,
        "cascade_archive": true,
        "cascade_restore": true,
        "auto_archive_related": true,
        "archive_after_days": null,
        "show_archived_in_list": true,
        "show_archived_in_search": false,
        "allow_restore": true,
        "require_reason": true,
        "archive_permission": null,
        "restore_permission": null,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
]
```

#### Создание конфигурации
```
POST /api/v1/archive-configurations/
```

**Тело запроса:**
```json
{
    "content_type": 1,
    "is_archivable": true,
    "cascade_archive": true,
    "cascade_restore": true,
    "auto_archive_related": true,
    "archive_after_days": 30,
    "show_archived_in_list": true,
    "show_archived_in_search": false,
    "allow_restore": true,
    "require_reason": true,
    "archive_permission": "patients.can_archive_patient",
    "restore_permission": "patients.can_restore_patient"
}
```

#### Обновление конфигурации
```
PUT /api/v1/archive-configurations/{id}/
PATCH /api/v1/archive-configurations/{id}/
```

#### Сброс к значениям по умолчанию
```
POST /api/v1/archive-configurations/{id}/reset/
```

### 3. Действия архивирования

#### Архивирование записи
```
POST /api/v1/archive/record/
```

**Тело запроса:**
```json
{
    "app_label": "patients",
    "model_name": "patient",
    "pk": 123,
    "reason": "Пациент выписан",
    "cascade": true
}
```

**Пример ответа:**
```json
{
    "success": true,
    "message": "Запись успешно архивирована",
    "record_id": 123,
    "archived_at": "2024-01-15T10:30:00Z"
}
```

#### Восстановление записи
```
POST /api/v1/archive/restore/
```

**Тело запроса:**
```json
{
    "app_label": "patients",
    "model_name": "patient",
    "pk": 123,
    "cascade": true
}
```

**Пример ответа:**
```json
{
    "success": true,
    "message": "Запись успешно восстановлена",
    "record_id": 123,
    "restored_at": "2024-01-15T10:30:00Z"
}
```

#### Массовое архивирование
```
POST /api/v1/archive/bulk/
```

**Тело запроса:**
```json
{
    "app_label": "patients",
    "model_name": "patient",
    "record_ids": [123, 124, 125],
    "reason": "Массовое архивирование выписанных пациентов",
    "cascade": true
}
```

**Пример ответа:**
```json
{
    "success": true,
    "archived_count": 3,
    "total_requested": 3,
    "message": "Успешно архивировано 3 из 3 записей"
}
```

#### Получение статуса архивирования
```
GET /api/v1/archive/status/?app_label=patients&model_name=patient&pk=123
```

**Пример ответа:**
```json
{
    "is_archived": true,
    "archived_at": "2024-01-15T10:30:00Z",
    "archived_by": {
        "id": 1,
        "username": "doctor_smith",
        "first_name": "John",
        "last_name": "Smith",
        "full_name": "John Smith",
        "email": "john.smith@hospital.com"
    },
    "archive_reason": "Пациент выписан"
}
```

## Коды ошибок

### 400 Bad Request
- Неверные параметры запроса
- Отсутствуют обязательные поля
- Модель не поддерживает архивирование

### 401 Unauthorized
- Пользователь не авторизован

### 403 Forbidden
- Недостаточно прав для выполнения действия

### 404 Not Found
- Запись не найдена
- Модель не найдена

### 500 Internal Server Error
- Внутренняя ошибка сервера

## Примеры использования

### JavaScript (Fetch API)
```javascript
// Архивирование записи
const archiveRecord = async (appLabel, modelName, pk, reason) => {
    const response = await fetch('/api/v1/archive/record/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            app_label: appLabel,
            model_name: modelName,
            pk: pk,
            reason: reason,
            cascade: true
        })
    });
    
    return await response.json();
};

// Получение логов архивирования
const getArchiveLogs = async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await fetch(`/api/v1/archive-logs/?${queryString}`);
    return await response.json();
};
```

### Python (requests)
```python
import requests

# Архивирование записи
def archive_record(app_label, model_name, pk, reason, session):
    response = session.post('/api/v1/archive/record/', json={
        'app_label': app_label,
        'model_name': model_name,
        'pk': pk,
        'reason': reason,
        'cascade': True
    })
    return response.json()

# Получение статистики
def get_archive_statistics(session):
    response = session.get('/api/v1/archive-logs/statistics/')
    return response.json()
```

## Безопасность

### Разрешения
- `archive-logs` - просмотр логов (требует аутентификации)
- `archive-configurations` - управление конфигурацией (требует права администратора)
- `archive-actions` - выполнение действий архивирования (требует соответствующих разрешений)

### Валидация
- Все входные данные валидируются
- Проверка прав доступа на уровне модели
- Логирование всех действий

### Rate Limiting
- Ограничение на количество запросов в минуту
- Защита от DDoS атак

## Версионирование

API использует версионирование в URL. Текущая версия: `v1`

При внесении изменений в API будет создана новая версия, а старая останется доступной для обратной совместимости.

## Поддержка

Для получения поддержки по API обращайтесь к документации проекта или создайте issue в репозитории.
