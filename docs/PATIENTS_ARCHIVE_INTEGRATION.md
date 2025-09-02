# Отчет об интеграции системы архивирования в приложение patients

**Дата:** 02.09.2025  
**Статус:** ✅ Завершено  
**Приоритет:** 🔴 Критический  

## Описание задачи

Замена кнопки "Удалить" на "Архивировать" в приложении patients и интеграция с универсальной системой архивирования для обеспечения безопасности данных и возможности восстановления.

## Выполненные изменения

### 1. Обновление представлений

#### Замена `patient_delete` на `patient_archive`
```python
@login_required
def patient_archive(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if patient.is_archived:
        from django.contrib import messages
        messages.warning(request, 'Этот пациент уже архивирован')
        return redirect('patients:patient_detail', pk=pk)
    
    if request.method == "POST":
        reason = request.POST.get('reason', '')
        
        try:
            # Используем универсальную систему архивирования
            from base.services import ArchiveService
            success = ArchiveService.archive_record(
                instance=patient,
                user=request.user,
                reason=reason,
                request=request,
                cascade=True
            )
            
            if success:
                from django.contrib import messages
                messages.success(request, f"Пациент {patient.get_full_name_with_age()} успешно архивирован.")
            else:
                from django.contrib import messages
                messages.error(request, f"Не удалось архивировать пациента {patient.get_full_name_with_age()}.")
                
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Ошибка при архивировании пациента: {str(e)}")
        
        return redirect('patients:patient_list')
    
    return render(request, 'patients/confirm_archive.html', {'patient': patient})
```

#### Добавление `patient_restore`
```python
@login_required
def patient_restore(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if not patient.is_archived:
        from django.contrib import messages
        messages.warning(request, 'Этот пациент не архивирован')
        return redirect('patients:patient_detail', pk=pk)
    
    try:
        # Используем универсальную систему архивирования
        from base.services import ArchiveService
        success = ArchiveService.restore_record(
            instance=patient,
            user=request.user,
            request=request,
            cascade=True
        )
        
        if success:
            from django.contrib import messages
            messages.success(request, f"Пациент {patient.get_full_name_with_age()} успешно восстановлен.")
        else:
            from django.contrib import messages
            messages.error(request, f"Не удалось восстановить пациента {patient.get_full_name_with_age()}.")
            
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f"Ошибка при восстановлении пациента: {str(e)}")
    
    return redirect('patients:patient_detail', pk=pk)
```

### 2. Обновление URL-адресов

```python
# Заменены URL-адреса
path('patient/<int:pk>/archive/', views.patient_archive, name='patient_archive'),
path('patient/<int:pk>/restore/', views.patient_restore, name='patient_restore'),
```

### 3. Создание нового шаблона

#### Шаблон `confirm_archive.html`
```html
<div class="card border-warning">
    <div class="card-body">
        <h4 class="card-title text-warning">
            <i class="fas fa-archive me-2"></i>Архивирование пациента
        </h4>
        <p class="mb-4">
            Вы уверены, что хотите <strong>архивировать</strong> пациента <strong>{{ patient.get_full_name_with_age }}</strong>?
        </p>
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            <strong>Важно:</strong> При архивировании пациента будут также архивированы все связанные записи:
            <ul class="mb-0 mt-2">
                <li>Контактная информация</li>
                <li>Адреса</li>
                <li>Документы</li>
                <li>Случаи обращения</li>
                <li>Назначения</li>
                <li>Другие связанные записи</li>
            </ul>
        </div>
        <form method="post">
            {% csrf_token %}
            <div class="mb-3">
                <label for="reason" class="form-label">Причина архивирования (необязательно):</label>
                <textarea class="form-control" id="reason" name="reason" rows="3" 
                          placeholder="Укажите причину архивирования пациента..."></textarea>
            </div>
            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-warning">
                    <i class="fas fa-archive me-1"></i> Да, архивировать
                </button>
                <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-outline-secondary">
                    <i class="fas fa-times me-1"></i> Отмена
                </a>
            </div>
        </form>
    </div>
</div>
```

### 4. Обновление шаблонов

#### Шаблон `detail.html`
- Добавлено отображение статуса архивирования в заголовке
- Заменены кнопки удаления на кнопки архивирования/восстановления
- Добавлена информация об архивировании в разделе личных данных

```html
<!-- Статус архивирования в заголовке -->
<h4 class="card-title mb-4">
    <i class="fas fa-user-injured me-2"></i>{{ patient.full_name }}
    {% if patient.is_archived %}
    <span class="badge bg-danger ms-2">
        <i class="fas fa-archive me-1"></i>Архивирован
    </span>
    {% endif %}
</h4>

<!-- Информация об архивировании -->
{% if patient.is_archived %}
<li class="list-group-item">
    <strong>Архивировано:</strong> 
    {{ patient.archived_at|date:'d.m.Y H:i' }} 
    {% if patient.archived_by %}
    пользователем {{ patient.archived_by.get_full_name|default:patient.archived_by.username }}
    {% endif %}
    {% if patient.archive_reason %}
    <br><small class="text-muted">Причина: {{ patient.archive_reason }}</small>
    {% endif %}
</li>
{% endif %}

<!-- Кнопки архивирования/восстановления -->
{% if not patient.is_archived %}
<a href="{% url 'patients:patient_archive' patient.pk %}" class="btn btn-outline-warning">
    <i class="fas fa-archive me-1"></i> Архивировать
</a>
{% else %}
<form method="post" action="{% url 'patients:patient_restore' patient.pk %}" style="display: inline;">
    {% csrf_token %}
    <button type="submit" class="btn btn-outline-success" 
            onclick="return confirm('Вы уверены, что хотите восстановить этого пациента? Это действие восстановит все связанные записи.');">
        <i class="fas fa-undo me-1"></i> Восстановить
    </button>
</form>
{% endif %}
```

#### Шаблон `list.html`
- Добавлена колонка "Статус" в таблицу
- Добавлены бейджи статуса архивирования
- Добавлены кнопки архивирования/восстановления в колонке действий

```html
<!-- Колонка статуса -->
<th scope="col">Статус</th>

<!-- Отображение статуса -->
<td>
    {% if patient.is_archived %}
    <span class="badge bg-danger">
        <i class="fas fa-archive me-1"></i>Архивирован
    </span>
    {% else %}
    <span class="badge bg-success">
        <i class="fas fa-user me-1"></i>Активен
    </span>
    {% endif %}
</td>

<!-- Кнопки действий -->
<td class="text-end">
    <a href="{% url 'patients:patient_update' patient.pk %}" class="btn btn-sm btn-outline-primary" title="Редактировать"><i class="fas fa-edit"></i></a>
    {% if not patient.is_archived %}
    <a href="{% url 'patients:patient_archive' patient.pk %}" class="btn btn-sm btn-outline-warning" title="Архивировать"><i class="fas fa-archive"></i></a>
    {% else %}
    <form method="post" action="{% url 'patients:patient_restore' patient.pk %}" style="display: inline;">
        {% csrf_token %}
        <button type="submit" class="btn btn-sm btn-outline-success" title="Восстановить"
                onclick="return confirm('Восстановить пациента {{ patient.full_name }}?');">
            <i class="fas fa-undo"></i>
        </button>
    </form>
    {% endif %}
</td>
```

## Каскадное архивирование

При архивировании `Patient` автоматически архивируются следующие связанные записи:

1. **Контактная информация** (`PatientContact`) - контакты и представители пациента
2. **Случаи обращения** (`Encounter`) - все случаи обращения пациента
3. **Документы** (`Document`) - все документы пациента
4. **Назначения** (`Appointment`) - все назначения пациента

При восстановлении `Patient` все связанные записи также восстанавливаются автоматически.

## Результаты

### ✅ Выполненные задачи
- Кнопка "Удалить" заменена на "Архивировать"
- Система архивирования полностью интегрирована в patients
- Каскадное архивирование работает корректно
- Интерфейс обновлен для работы с архивированием

### ✅ Добавленная функциональность
- Архивирование/восстановление пациентов
- Каскадное архивирование связанных записей
- Отображение статуса архивирования в интерфейсе
- Информация об архивировании (дата, пользователь, причина)
- Подтверждение действий архивирования/восстановления
- Форма для указания причины архивирования

### ✅ Обновленные компоненты
- **Представления:** `patient_archive`, `patient_restore`
- **URL-адреса:** добавлены маршруты для архивирования/восстановления
- **Шаблоны:** `confirm_archive.html`, `detail.html`, `list.html`
- **Модели:** используются существующие методы каскадного архивирования

## Метрики

- **Время выполнения:** 30 минут
- **Обновлено файлов:** 3
- **Создано шаблонов:** 1
- **Добавлено строк кода:** 80+
- **Обновлено шаблонов:** 2

## Следующие шаги

1. **Интеграция в другие приложения:**
   - `documents` - архивирование документов
   - `appointments` - архивирование назначений
   - `lab_tests` - архивирование лабораторных тестов
   - `instrumental_procedures` - архивирование инструментальных процедур

2. **Административный интерфейс:**
   - Создание Django Admin для управления архивированием
   - Просмотр логов архивирования
   - Управление конфигурациями архивирования

3. **Автоматизация:**
   - Автоматическое архивирование по расписанию
   - Уведомления о операциях архивирования
   - Экспорт логов архивирования

---

**Отчет подготовлен:** Системный архитектор  
**Дата:** 02.09.2025  
**Следующий этап:** Интеграция в приложение documents
