# 🖨️ Функционал печати документов

## 📋 Обзор

Система печати документов предоставляет полный набор инструментов для создания, просмотра и печати клинических документов в различных форматах.

## 🚀 Основные возможности

### 1. **Генерация PDF документов**
- Автоматическое создание PDF из данных документа
- Поддержка различных размеров шрифта и полей
- Настраиваемая ориентация страницы (книжная/альбомная)
- Автоматическое разбиение на страницы

### 2. **Предварительный просмотр**
- HTML-версия документа для просмотра перед печатью
- Адаптивный дизайн для экрана и печати
- Интерактивные элементы управления

### 3. **Настройки печати**
- Размер шрифта (10pt - 16pt)
- Поля страницы (узкие, обычные, широкие)
- Включение/исключение заголовка и подписи
- Ориентация страницы

### 4. **Управление документами**
- Список всех документов с возможностью печати
- Фильтрация по типу документа
- Поиск по названию
- Быстрые действия (клик по строке)

## 🛠️ Техническая реализация

### Сервисы

#### `DocumentPrintService`
Основной сервис для генерации PDF документов:

```python
from documents.services import DocumentPrintService

# Создание сервиса
print_service = DocumentPrintService()

# Генерация PDF
pdf_bytes = print_service.generate_pdf(clinical_document)
```

**Основные методы:**
- `generate_pdf()` - создает PDF документ
- `_add_header()` - добавляет заголовок
- `_add_document_content()` - добавляет содержимое
- `_add_footer()` - добавляет подпись

#### `DocumentTemplateService`
Сервис для работы с шаблонами печати:

```python
from documents.services import DocumentTemplateService

template_service = DocumentTemplateService()
template_name = template_service.get_print_template(document_type)
```

### Представления

#### `DocumentPrintView`
Генерирует и возвращает PDF документ для скачивания.

**URL:** `/documents/print/<int:document_id>/`

#### `DocumentPrintPreviewView`
Отображает HTML-версию документа для предварительного просмотра.

**URL:** `/documents/print/preview/<int:document_id>/`

#### `DocumentPrintSettingsView`
Позволяет настроить параметры печати и сгенерировать PDF с настройками.

**URL:** `/documents/print/settings/<int:document_id>/`

#### `DocumentPrintListView`
Список всех документов с возможностью печати.

**URL:** `/documents/print/list/`

## 📱 Интерфейс пользователя

### Кнопки печати в детальном просмотре документа

Каждый документ имеет набор кнопок для печати:

- **👁️ Просмотр** - открывает предварительный просмотр
- **📄 PDF** - скачивает PDF с стандартными настройками
- **⚙️ Настройки** - открывает страницу настроек печати

### Страница настроек печати

Интерактивная форма с настройками:

- **Размер шрифта** - от 10pt до 16pt
- **Ориентация страницы** - книжная или альбомная
- **Поля страницы** - узкие, обычные, широкие
- **Элементы документа** - включение заголовка и подписи

### Список документов для печати

Таблица с возможностями:

- Фильтрация по типу документа
- Поиск по названию
- Быстрые действия при клике на строку
- Пагинация для больших списков

## 🎨 Шаблоны печати

### Базовый шаблон

`base_print.html` - основной шаблон для всех документов:

- Адаптивные стили для экрана и печати
- Заголовок с метаданными
- Блок для содержимого документа
- Подпись и дата
- Элементы управления печатью

### Специфичные шаблоны

Создаются для каждого типа документа:

```
documents/print/
├── base_print.html          # Базовый шаблон
├── discharge_summary.html   # Выписка пациента
├── prescription.html        # Рецепт
├── referral.html           # Направление
└── ...
```

### Пример создания шаблона

```html
{% extends 'documents/print/base_print.html' %}

{% block document_content %}
<div class="field-group">
    <div class="field-label">Название поля:</div>
    <div class="field-value">
        {{ data.field_name|default:"Не указано" }}
    </div>
</div>
{% endblock %}
```

## 🔧 Настройка и кастомизация

### Добавление нового типа документа

1. **Создать модель в `models.py`:**
```python
class DocumentType(models.Model):
    name = models.CharField("Название", max_length=255)
    schema = models.JSONField("Схема полей")
```

2. **Создать шаблон печати:**
```html
<!-- documents/print/new_document_type.html -->
{% extends 'documents/print/base_print.html' %}
{% block document_content %}
<!-- Содержимое документа -->
{% endblock %}
```

3. **Добавить URL маршрут:**
```python
# urls.py
path('print/<int:document_id>/', views.DocumentPrintView.as_view(), name='document_print'),
```

### Настройка стилей печати

Стили настраиваются в `base_print.html`:

```css
@media print {
    body {
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
        margin: 2cm;
    }
    
    .no-print {
        display: none !important;
    }
}
```

## 📊 Примеры использования

### 1. Печать выписки пациента

```python
# В представлении
from documents.services import DocumentPrintService

def print_discharge(request, document_id):
    document = get_object_or_404(ClinicalDocument, pk=document_id)
    print_service = DocumentPrintService()
    pdf_bytes = print_service.generate_pdf(document)
    
    response = HttpResponse(pdf_bytes.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="discharge_{document.id}.pdf"'
    return response
```

### 2. Настройка параметров печати

```python
# В представлении настроек
print_settings = {
    'font_size': int(request.POST.get('font_size', 12)),
    'margins': request.POST.get('margins', 'normal'),
    'page_orientation': request.POST.get('page_orientation', 'portrait')
}

# Применение настроек
print_service = DocumentPrintService()
if print_settings['font_size'] != 12:
    print_service.font_size = print_settings['font_size']
```

### 3. Создание списка документов для печати

```python
# В представлении списка
documents = ClinicalDocument.objects.filter(
    author=request.user
).select_related(
    'document_type', 'author'
).order_by('-datetime_document')

# Фильтрация
if document_type_filter:
    documents = documents.filter(document_type_id=document_type_filter)
```

## 🚨 Обработка ошибок

### Основные исключения

- **Документ не найден** - 404 ошибка
- **Доступ запрещен** - 403 ошибка (проверка прав)
- **Ошибка генерации PDF** - 500 ошибка с описанием

### Логирование

Все ошибки логируются в консоль:

```python
try:
    pdf_bytes = print_service.generate_pdf(clinical_document)
except Exception as e:
    print(f"Ошибка при генерации PDF: {e}")
    raise
```

## 🔒 Безопасность

### Проверка прав доступа

- Только авторизованные пользователи
- Проверка авторства документа
- Специальные права для администраторов

```python
@method_decorator(login_required, name='dispatch')
class DocumentPrintView(View):
    def get(self, request, document_id):
        if not request.user.is_staff and clinical_document.author != request.user:
            return HttpResponse("Доступ запрещен", status=403)
```

## 📈 Производительность

### Оптимизации

- Использование `select_related` для связанных объектов
- Кэширование шаблонов
- Асинхронная генерация PDF для больших документов

### Мониторинг

- Логирование времени генерации
- Отслеживание использования памяти
- Метрики производительности

## 🚀 Планы развития

### Версия 2.0

- [ ] Массовая печать документов
- [ ] Электронная подпись
- [ ] Шаблоны для различных форматов бумаги
- [ ] Интеграция с принтерами
- [ ] Архивирование PDF документов

### Версия 2.1

- [ ] Поддержка водяных знаков
- [ ] Шифрование PDF
- [ ] Автоматическая отправка по email
- [ ] API для внешних систем

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи Django сервера
2. Убедитесь в корректности данных документа
3. Проверьте права доступа пользователя
4. Обратитесь к администратору системы

---

**Автор:** Система документооборота МедКарт  
**Версия:** 1.0  
**Дата:** {{ current_date }} 