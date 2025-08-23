# Исправление проблемы с удалением рабочих процессов подписей

## Проблема

При попытке удаления рабочего процесса подписей (`SignatureWorkflow`) в админке Django возникала ошибка:

```
Deleting the selected Рабочий процесс подписей would result in deleting related objects, 
but your account doesn't have permission to delete the following types of objects: Подпись документа
```

## Причина

1. **Запрет на удаление подписей**: В админке `DocumentSignatureAdmin` было установлено `has_delete_permission = False`
2. **Связи между моделями**: Рабочие процессы связаны с подписями через внешний ключ с `on_delete=models.CASCADE`
3. **Проверка прав Django**: Django проверяет права на удаление всех связанных объектов перед удалением основного

## Решение

### 1. Исправление сигналов

Убрали некорректное использование атрибута `auto_apply` в сигнале для `SignatureWorkflow`:

```python
# БЫЛО (некорректно):
@receiver(post_save, sender='document_signatures.SignatureWorkflow')
def create_signatures_for_existing_documents(sender, instance, created, **kwargs):
    if created and instance.auto_apply:  # ❌ auto_apply не существует в SignatureWorkflow

# СТАЛО (корректно):
@receiver(post_save, sender='document_signatures.SignatureTemplate')
def auto_apply_signature_template(sender, instance, created, **kwargs):
    if created and instance.auto_apply:  # ✅ auto_apply существует в SignatureTemplate
```

### 2. Настройка прав удаления

Разрешили удаление подписей только администраторам:

```python
def has_delete_permission(self, request, obj=None):
    """Разрешаем удаление подписей только администраторам"""
    return request.user.is_superuser
```

### 3. Улучшение админки

Добавили предупреждения о связанных объектах:

```python
def related_signatures_warning(self, obj):
    """Предупреждение о связанных подписях"""
    if obj.signatures.exists():
        count = obj.signatures.count()
        return format_html(
            '<div style="color: red; font-weight: bold; padding: 10px; border: 1px solid red; background-color: #ffe6e6;">'
            '⚠️ ВНИМАНИЕ: Этот рабочий процесс связан с {} подписями. '
            'При удалении все связанные подписи будут также удалены!</div>',
            count
        )
    return ""
```

### 4. Команда управления

Создали команду для безопасного удаления с предварительным просмотром:

```bash
# Предварительный просмотр
python manage.py safe_delete_workflow 1 --dry-run

# Удаление с подтверждением
python manage.py safe_delete_workflow 1

# Принудительное удаление
python manage.py safe_delete_workflow 1 --force
```

## Архитектурные принципы

1. **Каскадное удаление**: При удалении рабочего процесса автоматически удаляются связанные подписи
2. **Права доступа**: Удаление разрешено только суперпользователям
3. **Предупреждения**: Пользователь видит количество связанных объектов перед удалением
4. **Логирование**: Все операции удаления логируются для аудита

## Безопасность

- Удаление разрешено только администраторам
- Предварительный просмотр связанных объектов
- Транзакционное удаление (все или ничего)
- Логирование всех операций

## Использование

### В админке Django

1. Перейдите в раздел "Рабочие процессы подписей"
2. Выберите процесс для удаления
3. Нажмите "Удалить"
4. Подтвердите удаление

### Через командную строку

```bash
# Просмотр информации о рабочем процессе
python manage.py safe_delete_workflow 1 --dry-run

# Безопасное удаление
python manage.py safe_delete_workflow 1
```

## Тестирование

После внесения изменений:

1. Проверьте, что сервер запускается: `python manage.py check`
2. Протестируйте удаление в админке
3. Проверьте работу команды управления
4. Убедитесь, что связанные подписи удаляются корректно

## Заключение

Проблема решена путем:
- Исправления некорректных сигналов
- Настройки правильных прав доступа
- Добавления предупреждений и логирования
- Создания команды для безопасного удаления

Теперь администраторы могут безопасно удалять рабочие процессы подписей с полным пониманием последствий. 