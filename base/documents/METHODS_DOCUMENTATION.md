# Детальная документация методов модуля Documents

## Модели (Models)

### DocumentType

#### `__str__()`
**Назначение**: Строковое представление типа документа
**Возвращает**: `str` - форматированная строка с информацией о типе документа
**Формат**: "{name} ({department.name})" или "{name}" если отделение отсутствует
**Пример**: "Эпикриз (Кардиология)" или "Эпикриз"

### ClinicalDocument

#### `__str__()`
**Назначение**: Строковое представление клинического документа
**Возвращает**: `str` - форматированная строка с информацией о документе
**Формат**: "{document_type.name} от {datetime_document.strftime('%d.%m.%Y')}"
**Пример**: "Эпикриз от 15.01.2024"

### DocumentTemplate

#### `__str__()`
**Назначение**: Строковое представление шаблона документа
**Возвращает**: `str` - форматированная строка с информацией о шаблоне
**Формат**: "Шаблон '{name}' для '{document_type.name}'"
**Пример**: "Шаблон 'Стандартный эпикриз' для 'Эпикриз'"

## Представления (Views)

### DocumentTypeSelectionView

#### `get(request, model_name, object_id)`
**Назначение**: Отображение списка типов документов для выбора
**Параметры**:
- `request` - HTTP запрос
- `model_name` (str) - название модели связанного объекта
- `object_id` (int) - ID связанного объекта
**Логика**:
1. Получает ContentType по model_name
2. Получает родительский объект
3. Извлекает department_slug из GET параметров
4. Получает отделение по slug
5. Фильтрует типы документов по отделению
6. Применяет поиск по названию если передан параметр 'q'
**Контекст**:
- `document_types` - доступные типы документов
- `model_name` - название модели
- `object_id` - ID объекта
- `next_url` - URL для перенаправления
- `title` - заголовок страницы
- `search_query` - поисковый запрос

### DocumentCreateView

#### `get(request, model_name, object_id, document_type_id)`
**Назначение**: Отображение формы создания документа
**Параметры**:
- `request` - HTTP запрос
- `model_name` (str) - название модели связанного объекта
- `object_id` (int) - ID связанного объекта
- `document_type_id` (int) - ID типа документа
**Логика**:
1. Получает DocumentType по ID
2. Получает ContentType и родительский объект
3. Создает динамическую форму на основе схемы
4. Передает форму в контекст
**Контекст**:
- `form` - динамически созданная форма
- `document_type` - тип документа
- `title` - заголовок страницы

#### `post(request, model_name, object_id, document_type_id)`
**Назначение**: Обработка создания документа
**Параметры**: Те же что и в get()
**Логика**:
1. Создает динамическую форму и валидирует данные
2. Обрабатывает применение шаблона если нажата кнопка "Применить шаблон"
3. При валидной форме:
   - Извлекает datetime_document и template_choice
   - Преобразует Decimal в строки
   - Получает должность автора
   - Создает ClinicalDocument
   - Перенаправляет к next_url
4. При невалидной форме возвращает форму с ошибками

### DocumentDetailView

#### `get(request, pk)`
**Назначение**: Отображение деталей документа
**Параметры**:
- `request` - HTTP запрос
- `pk` (int) - ID документа
**Логика**:
1. Получает ClinicalDocument по ID
2. Создает динамическую форму на основе схемы
3. Заполняет форму данными из JSON-поля data
4. Передает форму в контекст для отображения
**Контекст**:
- `document` - объект документа
- `document_type` - тип документа
- `form` - заполненная форма для отображения
- `title` - заголовок страницы

### DocumentUpdateView

#### `dispatch(request, *args, **kwargs)`
**Назначение**: Проверка прав доступа перед обработкой запроса
**Логика**:
1. Получает документ по pk
2. Проверяет права доступа:
   - Суперпользователи могут редактировать любой документ
   - Обычные пользователи могут редактировать только свои документы
3. При отсутствии прав показывает ошибку и перенаправляет
**Возвращает**: HttpResponse или вызывает super().dispatch()

#### `get(request, pk)`
**Назначение**: Отображение формы редактирования документа
**Параметры**:
- `request` - HTTP запрос
- `pk` (int) - ID документа
**Логика**:
1. Создает динамическую форму на основе схемы
2. Заполняет форму данными из существующего документа
3. Передает форму в контекст
**Контекст**:
- `form` - заполненная форма для редактирования
- `document` - объект документа
- `document_type` - тип документа
- `title` - заголовок страницы

#### `post(request, pk)`
**Назначение**: Обработка редактирования документа
**Параметры**: Те же что и в get()
**Логика**:
1. Создает динамическую форму и валидирует данные
2. Обрабатывает применение шаблона
3. При валидной форме:
   - Обновляет datetime_document
   - Получает актуальную должность автора
   - Преобразует Decimal в строки
   - Сохраняет изменения в документе
   - Перенаправляет к next_url
4. При невалидной форме возвращает форму с ошибками

### DocumentDeleteView

#### `dispatch(request, *args, **kwargs)`
**Назначение**: Проверка прав доступа для удаления
**Логика**: Аналогично DocumentUpdateView.dispatch()

#### `get(request, pk)`
**Назначение**: Отображение страницы подтверждения удаления
**Параметры**:
- `request` - HTTP запрос
- `pk` (int) - ID документа
**Контекст**:
- `document` - объект документа для удаления
- `title` - заголовок страницы

## Формы (Forms)

### build_document_form(schema, document_type=None, user=None)
**Назначение**: Динамическое создание Django-формы на основе JSON-схемы
**Параметры**:
- `schema` (dict) - JSON-схема документа
- `document_type` (DocumentType) - тип документа (опционально)
- `user` (User) - пользователь (опционально)
**Возвращает**: `type` - класс динамически созданной формы
**Логика**:
1. Создает базовые поля (datetime_document, template_choice)
2. Обрабатывает каждое поле из схемы:
   - Извлекает name, type, label, required
   - Определяет класс поля по FIELD_TYPE_MAP
   - Настраивает параметры поля
   - Обрабатывает специальные поля (doctor, choice)
3. Создает класс формы с помощью type()
4. Добавляет логику фильтрации шаблонов в __init__
**Пример использования**:
```python
DocumentForm = build_document_form(schema, document_type, user)
form = DocumentForm()
```

### FIELD_TYPE_MAP
**Назначение**: Словарь соответствия типов полей схемы и классов Django-форм
**Содержимое**:
```python
FIELD_TYPE_MAP = {
    'text': forms.CharField,
    'textarea': lambda **kwargs: forms.CharField(widget=forms.Textarea, **kwargs),
    'number': forms.IntegerField,
    'decimal': forms.DecimalField,
    'date': forms.DateField,
    'datetime': forms.DateTimeField,
    'checkbox': forms.BooleanField,
    'choice': forms.ChoiceField,
}
```

## Утилиты (Utilities)

### convert_decimals_to_str(data)
**Назначение**: Рекурсивное преобразование объектов Decimal в строки
**Параметры**: `data` - данные для преобразования (dict, list, Decimal, или другой тип)
**Возвращает**: Преобразованные данные того же типа
**Логика**:
1. Если data - словарь: рекурсивно обрабатывает все значения
2. Если data - список: рекурсивно обрабатывает все элементы
3. Если data - Decimal: преобразует в строку
4. Иначе возвращает data без изменений
**Пример**:
```python
data = {
    'temperature': Decimal('36.6'),
    'measurements': [Decimal('120'), Decimal('80')]
}
result = convert_decimals_to_str(data)
# Результат: {'temperature': '36.6', 'measurements': ['120', '80']}
```

## Админ-панель (Admin)

### DocumentTypeAdmin

#### `list_display`
**Поля**: name, department
**Функционал**: Отображение названия и отделения в списке

#### `list_filter`
**Поля**: department
**Функционал**: Фильтрация по отделениям

#### `search_fields`
**Поля**: name
**Функционал**: Поиск по названию типа документа

### ClinicalDocumentAdmin

#### `list_display`
**Поля**: document_type, author, datetime_document, is_signed
**Функционал**: Отображение основных полей документа

#### `list_filter`
**Поля**: document_type, author, is_signed, datetime_document
**Функционал**: Фильтрация по типу, автору, статусу подписания, дате

#### `search_fields`
**Поля**: document_type__name, data
**Функционал**: Поиск по названию типа документа и содержимому данных

#### `readonly_fields`
**Поля**: created_at, updated_at
**Функционал**: Защита полей от редактирования

### DocumentTemplateAdmin

#### `list_display`
**Поля**: name, document_type, author, is_global
**Функционал**: Отображение основных полей шаблона

#### `list_filter`
**Поля**: document_type, author, is_global
**Функционал**: Фильтрация по типу документа, автору, флагу глобальности

#### `search_fields`
**Поля**: name, document_type__name
**Функционал**: Поиск по названию шаблона и типу документа

## Примеры использования

### Создание типа документа с JSON-схемой
```python
schema = {
    "fields": [
        {
            "name": "patient_name",
            "type": "text",
            "label": "ФИО пациента",
            "required": True
        },
        {
            "name": "diagnosis",
            "type": "textarea",
            "label": "Диагноз",
            "required": True
        },
        {
            "name": "temperature",
            "type": "decimal",
            "label": "Температура",
            "required": False
        },
        {
            "name": "blood_pressure",
            "type": "choice",
            "label": "Артериальное давление",
            "required": False,
            "options": ["Нормальное", "Повышенное", "Пониженное"]
        }
    ]
}

document_type = DocumentType.objects.create(
    name="Осмотр пациента",
    department=cardiology_department,
    schema=schema
)
```

### Создание шаблона документа
```python
template = DocumentTemplate.objects.create(
    name="Стандартный осмотр",
    document_type=document_type,
    author=user,
    is_global=True,
    template_data={
        "patient_name": "",
        "diagnosis": "ИБС, стенокардия напряжения",
        "temperature": "36.6",
        "blood_pressure": "Нормальное"
    }
)
```

### Создание клинического документа
```python
document = ClinicalDocument.objects.create(
    document_type=document_type,
    content_object=patient,  # GenericForeignKey
    author=user,
    author_position="Врач-кардиолог",
    datetime_document=timezone.now(),
    data={
        "patient_name": "Иванов И.И.",
        "diagnosis": "Острый инфаркт миокарда",
        "temperature": "37.2",
        "blood_pressure": "Повышенное"
    }
)
```

### Динамическое создание формы
```python
# Создание формы на основе схемы
DocumentForm = build_document_form(
    schema=document_type.schema,
    document_type=document_type,
    user=request.user
)

# Создание экземпляра формы
form = DocumentForm()

# Обработка POST данных
if request.method == 'POST':
    form = DocumentForm(request.POST)
    if form.is_valid():
        # Обработка валидных данных
        pass
```

### Применение шаблона
```python
# В представлении при обработке POST
if 'apply_template' in request.POST:
    template_id = request.POST.get('template_choice')
    if template_id:
        template = DocumentTemplate.objects.get(pk=template_id)
        initial_data = template.template_data.copy()
        # Сохраняем текущую дату документа
        if 'datetime_document' in request.POST:
            initial_data['datetime_document'] = request.POST['datetime_document']
        form = DocumentForm(initial=initial_data)
```

### Преобразование Decimal в строки
```python
# Данные с Decimal объектами
data = {
    'temperature': Decimal('36.6'),
    'pulse': Decimal('72'),
    'measurements': [Decimal('120'), Decimal('80')]
}

# Преобразование для сохранения в JSONField
converted_data = convert_decimals_to_str(data)
# Результат: {'temperature': '36.6', 'pulse': '72', 'measurements': ['120', '80']}
```

### Работа с GenericForeignKey
```python
# Создание документа для пациента
document = ClinicalDocument.objects.create(
    document_type=document_type,
    content_object=patient,  # GenericForeignKey
    author=user,
    data={'diagnosis': 'ИБС'}
)

# Создание документа для отделения
document = ClinicalDocument.objects.create(
    document_type=document_type,
    content_object=department,  # GenericForeignKey
    author=user,
    data={'report': 'Отчет за месяц'}
)

# Получение связанного объекта
related_object = document.content_object  # Может быть Patient, Department, etc.
```

### Фильтрация документов по типу
```python
# Получение всех документов определенного типа
documents = ClinicalDocument.objects.filter(document_type=document_type)

# Получение документов для конкретного пациента
patient_documents = ClinicalDocument.objects.filter(
    content_type=ContentType.objects.get_for_model(Patient),
    object_id=patient.id
)

# Получение документов определенного автора
author_documents = ClinicalDocument.objects.filter(author=user)
``` 