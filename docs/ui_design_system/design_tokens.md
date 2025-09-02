# Design Tokens - МедКарт

## Обзор

Design tokens - это атомарные значения дизайна (цвета, шрифты, отступы, тени), которые служат единым источником истины для всех компонентов интерфейса.

## Структура

```css
:root {
  /* Основные цвета системы */
  --primary-color: #4361ee;           /* Основной синий */
  --primary-light: #4895ef;            /* Светлый синий */
  --secondary-color: #3f37c9;         /* Темный синий */
  --success-color: #4cc9f0;            /* Голубой */
  --danger-color: #f72585;             /* Розовый */
  --warning-color: #f8961e;            /* Оранжевый */
  --info-color: #43aa8b;               /* Зеленый */
  
  /* Нейтральные цвета */
  --dark-color: #1a1a2e;               /* Темный */
  --dark-light: #16213e;               /* Светло-темный */
  --gray-color: #e2e2e2;               /* Серый */
  --light-color: #f8f9fa;              /* Светлый */
  
  /* Фон и поверхности */
  --bg-primary: #f5f7fb;               /* Основной фон */
  --bg-secondary: #ffffff;              /* Вторичный фон */
  --bg-hover: rgba(67, 97, 238, 0.1);  /* Фон при наведении */
  --bg-active: rgba(67, 97, 238, 0.1); /* Активный фон */
  
  /* Текст */
  --text-primary: #333333;             /* Основной текст */
  --text-secondary: #555555;           /* Вторичный текст */
  --text-muted: #777777;               /* Приглушенный текст */
  --text-light: #999999;               /* Светлый текст */
  
  /* Границы */
  --border-color: #dddddd;             /* Цвет границ */
  --border-light: #eeeeee;             /* Светлые границы */
  --border-radius: 8px;                /* Радиус скругления */
  --border-radius-lg: 12px;            /* Большой радиус */
  --border-radius-sm: 4px;            /* Малый радиус */
  
  /* Тени */
  --shadow-sm: 0 2px 10px rgba(0, 0, 0, 0.05);    /* Малая тень */
  --shadow-md: 0 5px 20px rgba(0, 0, 0, 0.1);     /* Средняя тень */
  --shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.15);   /* Большая тень */
  --shadow-hover: 0 5px 20px rgba(0, 0, 0, 0.1);  /* Тень при наведении */
  
  /* Отступы */
  --spacing-xs: 4px;                   /* Очень малый отступ */
  --spacing-sm: 8px;                   /* Малый отступ */
  --spacing-md: 16px;                  /* Средний отступ */
  --spacing-lg: 24px;                  /* Большой отступ */
  --spacing-xl: 32px;                  /* Очень большой отступ */
  --spacing-xxl: 48px;                 /* Экстра большой отступ */
  
  /* Размеры компонентов */
  --sidebar-width: 280px;              /* Ширина сайдбара */
  --sidebar-collapsed-width: 80px;     /* Ширина свернутого сайдбара */
  --header-height: 70px;               /* Высота заголовка */
  --footer-height: 50px;               /* Высота подвала */
  
  /* Анимации */
  --transition-speed: 0.3s;            /* Скорость переходов */
  --transition-fast: 0.2s;             /* Быстрые переходы */
  --transition-slow: 0.5s;             /* Медленные переходы */
  
  /* Z-индексы */
  --z-dropdown: 1000;                  /* Выпадающие меню */
  --z-sticky: 1020;                    /* Закрепленные элементы */
  --z-fixed: 1030;                     /* Фиксированные элементы */
  --z-modal-backdrop: 1040;            /* Фон модального окна */
  --z-modal: 1050;                     /* Модальные окна */
  --z-popover: 1060;                   /* Всплывающие подсказки */
  --z-tooltip: 1070;                   /* Подсказки */
  
  /* Медицинские специфичные токены */
  --medical-primary: #4361ee;          /* Основной медицинский цвет */
  --medical-success: #4cc9f0;         /* Успешные действия */
  --medical-warning: #f8961e;         /* Предупреждения */
  --medical-danger: #f72585;          /* Опасность/ошибки */
  --medical-info: #43aa8b;            /* Информация */
  
  /* Статусы */
  --status-active: #4cc9f0;           /* Активный статус */
  --status-inactive: #777777;         /* Неактивный статус */
  --status-archived: #f72585;          /* Архивированный */
  --status-pending: #f8961e;          /* Ожидающий */
  --status-completed: #43aa8b;        /* Завершенный */
  
  /* Документы */
  --document-signed: #43aa8b;         /* Подписанный документ */
  --document-unsigned: #f8961e;       /* Неподписанный документ */
  --document-canceled: #f72585;       /* Аннулированный документ */
  
  /* Диагнозы */
  --diagnosis-main: #4361ee;          /* Основной диагноз */
  --diagnosis-complication: #f8961e;  /* Осложнение */
  --diagnosis-comorbidity: #43aa8b;   /* Сопутствующий диагноз */
}
```

## Использование в компонентах

### Карточки
```css
.card {
  background-color: var(--bg-secondary);
  border: none;
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-speed) ease;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-hover);
}
```

### Кнопки
```css
.btn-primary {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  border-radius: var(--border-radius);
  transition: all var(--transition-fast) ease;
}

.btn-primary:hover {
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
  transform: translateY(-1px);
}
```

### Формы
```css
.form-control {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  transition: all var(--transition-fast) ease;
}

.form-control:focus {
  border-color: var(--primary-light);
  box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}
```

### Бейджи статусов
```css
.badge.bg-success {
  background-color: var(--status-active) !important;
}

.badge.bg-danger {
  background-color: var(--status-archived) !important;
}

.badge.bg-warning {
  background-color: var(--status-pending) !important;
}

.badge.bg-info {
  background-color: var(--status-completed) !important;
}
```

## Адаптивность

```css
/* Мобильные устройства */
@media (max-width: 768px) {
  :root {
    --spacing-lg: 16px;
    --spacing-xl: 24px;
    --border-radius: 6px;
  }
}

/* Планшеты */
@media (max-width: 992px) {
  :root {
    --sidebar-width: 0px;
  }
}
```

## Темная тема (будущее)

```css
[data-theme="dark"] {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --text-primary: #ffffff;
  --text-secondary: #cccccc;
  --border-color: #333333;
}
```

## Генерация токенов

Для автоматической генерации CSS переменных из design tokens можно использовать:

```javascript
// Пример генерации токенов из JSON
const tokens = {
  colors: {
    primary: '#4361ee',
    secondary: '#3f37c9',
    // ...
  }
};

function generateCSSVariables(tokens) {
  let css = ':root {\n';
  Object.entries(tokens.colors).forEach(([key, value]) => {
    css += `  --${key}-color: ${value};\n`;
  });
  css += '}';
  return css;
}
```

## Интеграция с Django

```python
# context_processors.py
def design_tokens(request):
    """Добавляет design tokens в контекст шаблонов"""
    return {
        'DESIGN_TOKENS': {
            'primary_color': '#4361ee',
            'secondary_color': '#3f37c9',
            'success_color': '#4cc9f0',
            'danger_color': '#f72585',
            'warning_color': '#f8961e',
            'info_color': '#43aa8b',
        }
    }
```

## Валидация

Для проверки корректности использования токенов:

```javascript
// Проверка использования CSS переменных
function validateTokenUsage() {
  const styleSheets = document.styleSheets;
  const usedTokens = new Set();
  
  for (let sheet of styleSheets) {
    try {
      const rules = sheet.cssRules || sheet.rules;
      for (let rule of rules) {
        if (rule.style) {
          const cssText = rule.style.cssText;
          const matches = cssText.match(/var\(--[^)]+\)/g);
          if (matches) {
            matches.forEach(token => usedTokens.add(token));
          }
        }
      }
    } catch (e) {
      // CORS ограничения
    }
  }
  
  return Array.from(usedTokens);
}
```

## Версионирование

При изменении design tokens необходимо:

1. Обновить версию в документации
2. Создать миграционный план для существующих компонентов
3. Обновить все компоненты, использующие измененные токены
4. Провести тестирование на всех устройствах

## Примеры использования

### Создание нового компонента
```css
.medical-card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-lg);
  transition: all var(--transition-speed) ease;
}

.medical-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.medical-card__title {
  color: var(--text-primary);
  font-weight: 600;
  margin-bottom: var(--spacing-md);
}

.medical-card__status {
  color: var(--status-active);
  font-size: 0.875rem;
}
```

### Адаптация существующего компонента
```css
/* Было */
.old-button {
  background-color: #007bff;
  border-radius: 4px;
  padding: 8px 16px;
}

/* Стало */
.old-button {
  background-color: var(--primary-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-sm) var(--spacing-md);
}
```
