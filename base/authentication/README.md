# Система аутентификации МедКарт

## Описание

Система аутентификации для Django-приложения "МедКарт", интегрированная с существующей системой профилей врачей.

## Особенности

- **Интеграция с профилями врачей**: Работает с существующей моделью `DoctorProfile`
- **Безопасность**: Проверка прав доступа и валидация данных
- **Современный UI**: Адаптивный дизайн в стиле основного приложения
- **Анимации**: Плавные переходы и интерактивные элементы

## Структура

```
authentication/
├── models.py          # Модель UserProfile для расширенной информации
├── forms.py           # Форма аутентификации MedicalAuthenticationForm
├── views.py           # Представление MedicalLoginView
├── urls.py            # URL-маршруты для аутентификации
├── admin.py           # Административный интерфейс
├── templates/         # Шаблоны страниц
│   └── authentication/
│       └── login.html # Страница входа
└── static/            # Статические файлы
    └── authentication/
        ├── css/       # Стили
        │   └── login.css
        └── js/        # JavaScript
            └── login.js
```

## Использование

### URL-адреса

- **Вход**: `/auth/login/`
- **Выход**: `/auth/logout/`

### Настройки в settings.py

```python
# Настройки аутентификации
LOGIN_URL = 'authentication:login'
LOGIN_REDIRECT_URL = 'patients:home'
LOGOUT_REDIRECT_URL = 'authentication:login'

# Настройки сессии
SESSION_COOKIE_AGE = 3600  # 1 час
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
```

### Требования для входа

1. Пользователь должен существовать в системе Django
2. У пользователя должен быть активный профиль врача (`DoctorProfile`)
3. Аккаунт не должен быть заблокирован

## Интеграция с профилями врачей

Система автоматически:

- Проверяет наличие профиля врача при входе
- Отображает ФИО и должность из `DoctorProfile`
- Показывает приветственное сообщение с информацией о враче

## Администрирование

В Django Admin доступны:

- **User**: Расширенная информация о пользователях
- **UserProfile**: Дополнительные профили пользователей
- **DoctorProfile**: Профили врачей (из приложения profiles)

## Тестирование

### Тестовые данные

**Логин**: `admin`  
**Пароль**: `admin123`

### Создание тестового пользователя

```bash
# Создание суперпользователя
python manage.py createsuperuser --username admin --email admin@medkarta.ru

# Установка пароля
python manage.py shell -c "from django.contrib.auth.models import User; u = User.objects.get(username='admin'); u.set_password('admin123'); u.save()"

# Создание профиля врача
python manage.py shell -c "from django.contrib.auth.models import User; from profiles.models import DoctorProfile; from datetime import date; u = User.objects.get(username='admin'); dp = DoctorProfile.objects.create(user=u, full_name='Администратор Системы', specialization='Системный администратор', position='Главный администратор', employment_date=date.today())"
```

## Безопасность

- CSRF защита для всех форм
- Валидация данных на сервере и клиенте
- Проверка прав доступа
- Логирование попыток входа
- Настройки сессии для безопасности

## Кастомизация

### Изменение стилей

Редактируйте файл `static/authentication/css/login.css`

### Изменение анимаций

Редактируйте файл `static/authentication/js/login.js`

### Изменение шаблона

Редактируйте файл `templates/authentication/login.html`

## Поддержка

При возникновении проблем:

1. Проверьте логи Django
2. Убедитесь, что все миграции применены
3. Проверьте настройки в `settings.py`
4. Убедитесь, что у пользователя есть профиль врача

## Разработка

### Добавление новых полей

1. Обновите модель в `models.py`
2. Создайте и примените миграции
3. Обновите формы и представления
4. Обновите административный интерфейс

### Добавление новых функций

1. Создайте новые представления в `views.py`
2. Добавьте URL-маршруты в `urls.py`
3. Создайте шаблоны в `templates/`
4. Добавьте статические файлы в `static/`

