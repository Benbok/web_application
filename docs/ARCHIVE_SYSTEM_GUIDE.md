# Руководство по системе архивирования

**Версия документа:** 1.0  
**Дата создания:** 28.08.2025  
**Статус:** Активное руководство

## Обзор

Система архивирования заменяет удаление записей на их архивирование, что обеспечивает:
- **Сохранение данных** для аудита и соответствия требованиям
- **Каскадное архивирование** связанных записей
- **Возможность восстановления** из архива
- **Полное логирование** всех операций архивирования

## Архитектура системы

### Базовые модели

#### ArchivableModel
Абстрактная базовая модель для поддержки архивирования:

```python
class ArchivableModel(models.Model):
    is_archived = models.BooleanField("Архивировано", default=False)
    archived_at = models.DateTimeField("Дата архивирования", null=True, blank=True)
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    archive_reason = models.TextField("Причина архивирования", blank=True)
    
    class Meta:
        abstract = True
```

#### ArchiveLog
Модель для логирования операций архивирования:

```python
class ArchiveLog(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    action = models.CharField("Действие", max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField("Время действия", auto_now_add=True)
    reason = models.TextField("Причина", blank=True)
    # ... дополнительные поля для аудита
```

#### ArchiveConfiguration
Конфигурация архивирования для разных моделей:

```python
class ArchiveConfiguration(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, unique=True)
    is_archivable = models.BooleanField("Поддерживает архивирование", default=True)
    cascade_archive = models.BooleanField("Каскадное архивирование", default=True)
    cascade_restore = models.BooleanField("Каскадное восстановление", default=True)
    allow_restore = models.BooleanField("Разрешить восстановление", default=True)
    require_reason = models.BooleanField("Требовать причину", default=True)
    # ... дополнительные настройки
```

### Сервисы

#### ArchiveService
Основной сервис для управления архивированием:

```python
class ArchiveService:
    @classmethod
    def archive_record(cls, instance, user=None, reason="", request=None, cascade=True)
    @classmethod
    def restore_record(cls, instance, user=None, request=None, cascade=True)
    @classmethod
    def bulk_archive(cls, queryset, user=None, reason="", request=None)
    @classmethod
    def bulk_restore(cls, queryset, user=None, request=None)
```

#### ArchiveManager
Менеджер для QuerySet с поддержкой архивирования:

```python
class ArchiveManager(models.Manager):
    def active(self)  # Только активные записи
    def archived(self)  # Только архивированные записи
    def archive_record(self, instance, user=None, reason="", request=None)
    def restore_record(self, instance, user=None, request=None)
```

## Интеграция в существующие модели

### Пример: Модель Patient

```python
from base.models import ArchivableModel
from base.services import ArchiveManager

class Patient(ArchivableModel):
    # ... поля модели
    
    # Менеджер для архивирования
    objects = ArchiveManager()
    
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи пациента"""
        # Архивируем контакты пациента
        if hasattr(self, 'contact') and self.contact:
            if hasattr(self.contact, 'is_archived') and not self.contact.is_archived:
                self.contact.archive(user, f"Каскадное архивирование пациента: {reason}")
        
        # Архивируем встречи пациента
        from encounters.models import Encounter
        encounters = Encounter.objects.filter(patient=self, is_archived=False)
        for encounter in encounters:
            encounter.archive(user, f"Каскадное архивирование пациента: {reason}")
        
        # ... другие связанные записи
    
    def _restore_related_records(self, user):
        """Восстанавливает связанные записи пациента"""
        # Восстанавливаем контакты пациента
        if hasattr(self, 'contact') and self.contact:
            if hasattr(self.contact, 'is_archived') and self.contact.is_archived:
                self.contact.restore(user)
        
        # Восстанавливаем встречи пациента
        from encounters.models import Encounter
        encounters = Encounter.objects.filter(patient=self, is_archived=True)
        for encounter in encounters:
            encounter.restore(user)
        
        # ... другие связанные записи
```

## Использование в представлениях

### Архивирование записи

```python
from base.services import ArchiveService
from django.contrib import messages

def archive_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        form = ArchiveForm(request.POST, instance=patient, user=request.user)
        if form.is_valid():
            try:
                ArchiveService.archive_record(
                    instance=patient,
                    user=request.user,
                    reason=form.cleaned_data['reason'],
                    request=request,
                    cascade=form.cleaned_data.get('cascade', True)
                )
                messages.success(request, "Пациент успешно архивирован")
                return redirect('patients:patient_list')
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
    else:
        form = ArchiveForm(instance=patient, user=request.user)
    
    return render(request, 'patients/archive_form.html', {'form': form, 'patient': patient})
```

### Восстановление записи

```python
def restore_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        form = RestoreForm(request.POST, instance=patient, user=request.user)
        if form.is_valid():
            try:
                ArchiveService.restore_record(
                    instance=patient,
                    user=request.user,
                    request=request,
                    cascade=form.cleaned_data.get('cascade', True)
                )
                messages.success(request, "Пациент успешно восстановлен")
                return redirect('patients:patient_list')
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
    else:
        form = RestoreForm(instance=patient, user=request.user)
    
    return render(request, 'patients/restore_form.html', {'form': form, 'patient': patient})
```

### Массовое архивирование

```python
@require_POST
def bulk_archive_patients(request):
    patient_ids = request.POST.getlist('patient_ids')
    patients = Patient.objects.filter(pk__in=patient_ids)
    
    if request.method == 'POST':
        form = BulkArchiveForm(request.POST, queryset=patients, user=request.user)
        if form.is_valid():
            try:
                archived_count = ArchiveService.bulk_archive(
                    queryset=patients,
                    user=request.user,
                    reason=form.cleaned_data['reason'],
                    request=request
                )
                messages.success(request, f"Успешно архивировано {archived_count} пациентов")
                return redirect('patients:patient_list')
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
    else:
        form = BulkArchiveForm(queryset=patients, user=request.user)
    
    return render(request, 'patients/bulk_archive_form.html', {'form': form, 'patients': patients})
```

## Использование в шаблонах

### Кнопки архивирования

```html
<!-- Кнопка архивирования -->
<a href="{% url 'base:archive_record' 'patients' 'patient' patient.pk %}" 
   class="btn btn-warning btn-archive"
   data-record-name="{{ patient.full_name }}">
    <i class="fas fa-archive"></i> Архивировать
</a>

<!-- Кнопка восстановления -->
<a href="{% url 'base:restore_record' 'patients' 'patient' patient.pk %}" 
   class="btn btn-success btn-restore"
   data-record-name="{{ patient.full_name }}">
    <i class="fas fa-undo"></i> Восстановить
</a>

<!-- Массовое архивирование -->
<button class="btn btn-warning btn-bulk-archive" disabled>
    <i class="fas fa-archive"></i> Архивировать выбранных
</button>
```

### Чекбоксы для массового выбора

```html
<input type="checkbox" class="record-checkbox" 
       value="{{ patient.pk }}" 
       data-record-name="{{ patient.full_name }}">
```

### Отображение статуса архивирования

```html
{% if patient.is_archived %}
<div class="alert alert-warning">
    <i class="fas fa-archive"></i>
    Архивировано {{ patient.archived_at|date:"d.m.Y H:i" }}
    {% if patient.archived_by %}
    пользователем {{ patient.archived_by.get_full_name }}
    {% endif %}
    {% if patient.archive_reason %}
    <br><strong>Причина:</strong> {{ patient.archive_reason }}
    {% endif %}
</div>
{% endif %}
```

### Фильтрация по статусу

```html
<form method="get" class="mb-3">
    <div class="row">
        <div class="col-md-3">
            <select name="status" class="form-select">
                <option value="">Все записи</option>
                <option value="active" {% if request.GET.status == 'active' %}selected{% endif %}>
                    Активные
                </option>
                <option value="archived" {% if request.GET.status == 'archived' %}selected{% endif %}>
                    Архивированные
                </option>
            </select>
        </div>
        <div class="col-md-3">
            <input type="text" name="archive_reason" class="form-control" 
                   placeholder="Поиск по причине..."
                   value="{{ request.GET.archive_reason }}">
        </div>
        <div class="col-md-2">
            <button type="submit" class="btn btn-primary">Фильтровать</button>
        </div>
    </div>
</form>
```

## JavaScript интеграция

### Подключение скрипта

```html
<script src="{% static 'js/archive.js' %}"></script>
```

### Автоматическая инициализация

```javascript
// Скрипт автоматически инициализируется при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.archiveManager = new ArchiveManager();
});
```

### Ручное управление

```javascript
// Архивирование записи
const archiveManager = new ArchiveManager();
archiveManager.showArchiveModal('/archive/patients/patient/1/', 'Иванов Иван');

// Восстановление записи
archiveManager.showRestoreModal('/restore/patients/patient/1/', 'Иванов Иван');

// Массовое архивирование
const selectedRecords = archiveManager.getSelectedRecords();
archiveManager.showBulkArchiveModal(selectedRecords);
```

## URL-маршруты

### Базовые маршруты

```python
# base/urls.py
urlpatterns = [
    # Архивирование записей
    path('archive/<str:app_label>/<str:model_name>/<int:pk>/', 
         views.archive_record, name='archive_record'),
    path('restore/<str:app_label>/<str:model_name>/<int:pk>/', 
         views.restore_record, name='restore_record'),
    path('bulk-archive/<str:app_label>/<str:model_name>/', 
         views.bulk_archive, name='bulk_archive'),
    path('archive-list/<str:app_label>/<str:model_name>/', 
         views.archive_list, name='archive_list'),
    
    # Логи и конфигурация
    path('archive-logs/', views.archive_logs, name='archive_logs'),
    path('archive-configuration/', views.archive_configuration, name='archive_configuration'),
    
    # AJAX API
    path('archive-ajax/', views.archive_ajax, name='archive_ajax'),
]
```

### Примеры использования

```python
# Архивирование пациента
reverse('base:archive_record', kwargs={
    'app_label': 'patients', 
    'model_name': 'patient', 
    'pk': patient.pk
})

# Восстановление пациента
reverse('base:restore_record', kwargs={
    'app_label': 'patients', 
    'model_name': 'patient', 
    'pk': patient.pk
})

# Массовое архивирование пациентов
reverse('base:bulk_archive', kwargs={
    'app_label': 'patients', 
    'model_name': 'patient'
})

# Список архивированных пациентов
reverse('base:archive_list', kwargs={
    'app_label': 'patients', 
    'model_name': 'patient'
})
```

## Конфигурация

### Настройка модели

```python
# Создание конфигурации для модели
config = ArchiveConfiguration.get_config(Patient)

# Настройка параметров
config.is_archivable = True
config.cascade_archive = True
config.cascade_restore = True
config.allow_restore = True
config.require_reason = True
config.archive_permission = 'patients.can_archive_patient'
config.restore_permission = 'patients.can_restore_patient'
config.save()
```

### Права доступа

```python
# Создание разрешений
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

content_type = ContentType.objects.get_for_model(Patient)

# Разрешение на архивирование
Permission.objects.create(
    codename='can_archive_patient',
    name='Can archive patient',
    content_type=content_type,
)

# Разрешение на восстановление
Permission.objects.create(
    codename='can_restore_patient',
    name='Can restore patient',
    content_type=content_type,
)
```

## Логирование и аудит

### Просмотр логов

```python
from base.models import ArchiveLog

# Все логи архивирования
logs = ArchiveLog.objects.all()

# Логи конкретной модели
logs = ArchiveLog.objects.filter(content_type__model='patient')

# Логи конкретного пользователя
logs = ArchiveLog.objects.filter(user=request.user)

# Логи за период
from django.utils import timezone
from datetime import timedelta

logs = ArchiveLog.objects.filter(
    timestamp__gte=timezone.now() - timedelta(days=30)
)
```

### Аудит операций

```python
# Получение истории архивирования записи
logs = ArchiveLog.objects.filter(
    content_type=ContentType.objects.get_for_model(Patient),
    object_id=patient.pk
).order_by('-timestamp')

for log in logs:
    print(f"{log.timestamp}: {log.get_action_display()} - {log.reason}")
    if log.user:
        print(f"Пользователь: {log.user.get_full_name()}")
    if log.ip_address:
        print(f"IP: {log.ip_address}")
```

## Лучшие практики

### 1. Каскадное архивирование
- Всегда архивируйте связанные записи
- Используйте понятные причины архивирования
- Логируйте все операции

### 2. Восстановление
- Проверяйте права доступа перед восстановлением
- Восстанавливайте связанные записи
- Уведомляйте пользователей о восстановлении

### 3. Производительность
- Используйте индексы для полей архивирования
- Ограничивайте количество записей в массовых операциях
- Кешируйте часто используемые запросы

### 4. Безопасность
- Проверяйте права доступа на уровне представлений
- Логируйте IP-адреса и User-Agent
- Валидируйте входные данные

### 5. Пользовательский интерфейс
- Показывайте статус архивирования
- Предоставляйте понятные сообщения об ошибках
- Используйте подтверждения для критических операций

## Troubleshooting

### Проблемы с миграциями

```bash
# Создание миграций
python manage.py makemigrations

# Применение миграций
python manage.py migrate

# Проверка состояния миграций
python manage.py showmigrations
```

### Проблемы с правами доступа

```python
# Проверка прав пользователя
if request.user.has_perm('patients.can_archive_patient'):
    # Разрешено архивирование
    pass
else:
    # Запрещено архивирование
    raise PermissionDenied("Нет прав на архивирование")
```

### Проблемы с каскадным архивированием

```python
# Проверка связанных записей
related_records = []
for field in instance._meta.get_fields():
    if field.is_relation and hasattr(field.related_model, 'is_archived'):
        if field.many_to_many:
            related_objects = getattr(instance, field.name).all()
        else:
            related_objects = [getattr(instance, field.name)] if getattr(instance, field.name) else []
        
        for obj in related_objects:
            if obj and not obj.is_archived:
                related_records.append(obj)

print(f"Найдено {len(related_records)} связанных записей для архивирования")
```

## Заключение

Система архивирования обеспечивает безопасное управление данными в медицинской информационной системе. Следуя этому руководству, вы сможете эффективно интегрировать архивирование в любые модели Django и обеспечить соответствие требованиям аудита и безопасности.

---

**Документ подготовлен:** Системный архитектор  
**Дата создания:** 28.08.2025  
**Последнее обновление:** 28.08.2025

## Архивирование в админке Django

### Обзор
Система архивирования в админке Django позволяет администраторам легко архивировать и восстанавливать записи через веб-интерфейс админки.

### Доступные действия

#### 1. Массовое архивирование
- **Действие:** "Архивировать выбранные записи"
- **Описание:** Архивирует все выбранные записи, которые еще не архивированы
- **Логика:** Проверяет `is_archived=False` перед архивированием
- **Результат:** Устанавливает `is_archived=True`, `archived_at`, `archived_by`, `archive_reason`

#### 2. Массовое восстановление
- **Действие:** "Восстановить выбранные записи из архива"
- **Описание:** Восстанавливает все выбранные записи из архива
- **Логика:** Проверяет `is_archived=True` перед восстановлением
- **Результат:** Устанавливает `is_archived=False`, очищает поля архивирования

### Поддерживаемые модели

#### ExaminationPlan (Планы обследования)
```python
@admin.register(ExaminationPlan)
class ExaminationPlanAdmin(admin.ModelAdmin):
    actions = ['archive_selected', 'restore_selected']
    list_display = ['name', 'encounter', 'priority', 'is_archived', 'created_at']
    list_filter = ['priority', 'is_archived', 'created_at']
```

#### ExaminationLabTest (Лабораторные исследования)
```python
@admin.register(ExaminationLabTest)
class ExaminationLabTestAdmin(admin.ModelAdmin):
    actions = ['archive_selected', 'restore_selected']
    list_display = ['examination_plan', 'lab_test', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
```

#### ExaminationInstrumental (Инструментальные исследования)
```python
@admin.register(ExaminationInstrumental)
class ExaminationInstrumentalAdmin(admin.ModelAdmin):
    actions = ['archive_selected', 'restore_selected']
    list_display = ['examination_plan', 'instrumental_procedure', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
```

### Как использовать

#### Шаг 1: Переход в админку
1. Откройте Django Admin (`/admin/`)
2. Войдите с правами администратора
3. Перейдите в раздел "Examination management"

#### Шаг 2: Выбор записей
1. Выберите одну или несколько записей с помощью чекбоксов
2. Используйте фильтры для поиска нужных записей:
   - **Архивировано:** Да/Нет - для фильтрации по статусу архивирования
   - **Создано:** для фильтрации по дате создания

#### Шаг 3: Выполнение действия
1. В выпадающем списке "Действие" выберите:
   - "Архивировать выбранные записи" - для архивирования
   - "Восстановить выбранные записи из архива" - для восстановления
2. Нажмите "Выполнить"
3. Подтвердите действие в диалоговом окне

#### Шаг 4: Проверка результата
- Успешные операции отображаются зелеными сообщениями
- Ошибки отображаются красными сообщениями
- Количество обработанных записей показывается в сообщении

### Примеры использования

#### Архивирование плана обследования
```python
# В админке:
# 1. Выберите план обследования
# 2. Выберите действие "Архивировать выбранные записи"
# 3. Нажмите "Выполнить"

# Результат:
# - План помечен как архивированный
# - Все связанные исследования также архивируются
# - Сообщение: "Успешно архивировано 1 записей."
```

#### Восстановление лабораторного исследования
```python
# В админке:
# 1. Примените фильтр "Архивировано: Да"
# 2. Выберите лабораторное исследование
# 3. Выберите действие "Восстановить выбранные записи из архива"
# 4. Нажмите "Выполнить"

# Результат:
# - Исследование восстановлено из архива
# - Сообщение: "Успешно восстановлено 1 записей."
```

### Обработка ошибок

#### Типичные ошибки и их решения

1. **"Запись уже архивирована"**
   - **Причина:** Попытка архивировать уже архивированную запись
   - **Решение:** Система автоматически пропускает такие записи

2. **"Запись не архивирована"**
   - **Причина:** Попытка восстановить неархивированную запись
   - **Решение:** Система автоматически пропускает такие записи

3. **"Ошибка при архивировании записи"**
   - **Причина:** Проблемы с правами доступа или целостностью данных
   - **Решение:** Проверьте права пользователя и целостность данных

### Логирование операций

Все операции архивирования логируются:
- **Время операции:** Автоматически записывается в `archived_at`
- **Пользователь:** Записывается в `archived_by`
- **Причина:** Записывается в `archive_reason` (по умолчанию "Архивировано через админку")

### Безопасность

#### Права доступа
- Только пользователи с правами администратора могут выполнять действия архивирования
- Все операции выполняются от имени текущего пользователя
- Логируются все попытки архивирования/восстановления

#### Валидация данных
- Проверяется текущий статус записи перед операцией
- Предотвращается дублирование операций
- Обработка исключений для каждой записи отдельно

### Рекомендации

1. **Регулярное архивирование**
   - Архивируйте старые планы обследования
   - Архивируйте выполненные исследования
   - Поддерживайте актуальность данных

2. **Контроль архивирования**
   - Используйте фильтры для поиска нужных записей
   - Проверяйте результаты операций
   - Мониторьте логи архивирования

3. **Восстановление данных**
   - Восстанавливайте записи только при необходимости
   - Проверяйте целостность данных после восстановления
   - Документируйте причины восстановления

### Техническая реализация

#### Код действий
```python
def archive_selected(self, request, queryset):
    """Архивирует выбранные записи"""
    archived_count = 0
    for obj in queryset:
        if not obj.is_archived:
            try:
                obj.archive(user=request.user, reason="Архивировано через админку")
                archived_count += 1
            except Exception as e:
                messages.error(request, f"Ошибка при архивировании записи {obj.id}: {str(e)}")
    
    if archived_count > 0:
        messages.success(request, f"Успешно архивировано {archived_count} записей.")
    else:
        messages.warning(request, "Нет записей для архивирования.")

def restore_selected(self, request, queryset):
    """Восстанавливает выбранные записи из архива"""
    restored_count = 0
    for obj in queryset:
        if obj.is_archived:
            try:
                obj.restore(user=request.user)
                restored_count += 1
            except Exception as e:
                messages.error(request, f"Ошибка при восстановлении записи {obj.id}: {str(e)}")
    
    if restored_count > 0:
        messages.success(request, f"Успешно восстановлено {restored_count} записей.")
    else:
        messages.warning(request, "Нет записей для восстановления.")
```

#### Интеграция с ArchivableModel
Действия используют методы `archive()` и `restore()` из базового класса `ArchivableModel`:
- `archive(user, reason)` - архивирует запись и связанные записи
- `restore(user)` - восстанавливает запись и связанные записи

## Система архивирования в приложениях
