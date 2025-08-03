# Автоматическое заполнение полей дозировки при выборе препарата

## Проблема

При выборе препарата из справочника пользователю приходилось вручную заполнять все поля дозировки (дозировка, частота, путь введения, длительность, инструкции), что занимало много времени и могло привести к ошибкам.

## Решение

Добавлен функционал автоматического заполнения полей дозировки при выборе препарата из справочника. Система автоматически загружает стандартные дозировки из базы данных и заполняет соответствующие поля формы.

## Изменения в коде

### 1. Новый AJAX endpoint (base/encounters/urls.py)

```python
path('api/medication-info/<int:medication_id>/', views.MedicationInfoView.as_view(), name='medication_info'),
```

### 2. Новое представление MedicationInfoView (base/encounters/views.py)

```python
@method_decorator(csrf_exempt, name='dispatch')
class MedicationInfoView(View):
    """AJAX endpoint для получения информации о препарате"""
    
    def get(self, request, medication_id):
        try:
            from pharmacy.models import Medication
            medication = Medication.objects.get(pk=medication_id)
            
            # Получаем информацию о препарате
            medication_info = {
                'id': medication.id,
                'name': medication.name,
                'description': getattr(medication, 'description', ''),
                'dosage': '',
                'frequency': '',
                'route': 'oral',
                'duration': '',
                'instructions': ''
            }
            
            # Получаем торговые названия
            trade_names = medication.trade_names.all()
            if trade_names.exists():
                medication_info['trade_names'] = [
                    {
                        'name': tn.name,
                        'group': tn.medication_group.name if tn.medication_group else None,
                        'release_form': tn.release_form.name if tn.release_form else None,
                    }
                    for tn in trade_names
                ]
            
            # Получаем стандартные дозировки из pharmacy app
            from pharmacy.models import Regimen, DosingInstruction
            # Ищем схему с инструкциями по дозированию
            regimens_with_instructions = Regimen.objects.filter(
                medication=medication,
                dosing_instructions__isnull=False
            ).distinct()
            
            if regimens_with_instructions.exists():
                # Берем первую схему с инструкциями
                regimen = regimens_with_instructions.first()
                dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
                if dosing_instruction:
                    medication_info['dosage'] = dosing_instruction.dose_description
                    medication_info['frequency'] = dosing_instruction.frequency_description
                    medication_info['route'] = dosing_instruction.route.name if dosing_instruction.route else 'oral'
                    medication_info['duration'] = dosing_instruction.duration_description
                    medication_info['instructions'] = regimen.notes or ''
            
            return JsonResponse({
                'success': True,
                'medication': medication_info
            })
            
        except Medication.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Препарат не найден'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
```

### 3. Обновлен JavaScript в шаблонах

**В quick_add_medication.html:**
```javascript
// Функция для автоматического заполнения полей дозировки
async function loadMedicationInfo(medicationId) {
    if (!medicationId) {
        // Очищаем поля если препарат не выбран
        if (dosageField) dosageField.value = '';
        if (frequencyField) frequencyField.value = '';
        if (routeField) routeField.value = 'oral';
        if (durationField) durationField.value = '';
        if (instructionsField) instructionsField.value = '';
        return;
    }
    
    try {
        const response = await fetch(`{% url 'encounters:medication_info' 0 %}`.replace('0', medicationId));
        const data = await response.json();
        
        if (data.success && data.medication) {
            const med = data.medication;
            
            // Заполняем поля автоматически
            if (dosageField && med.dosage) dosageField.value = med.dosage;
            if (frequencyField && med.frequency) frequencyField.value = med.frequency;
            if (routeField && med.route) routeField.value = med.route;
            if (durationField && med.duration) durationField.value = med.duration;
            if (instructionsField && med.instructions) instructionsField.value = med.instructions;
            
            // Показываем уведомление о загрузке данных
            showNotification('Данные о препарате загружены автоматически', 'info');
        }
    } catch (error) {
        console.error('Ошибка при загрузке информации о препарате:', error);
        showNotification('Не удалось загрузить данные о препарате', 'warning');
    }
}
```

**В treatment_medication_form.html:**
Добавлен аналогичный JavaScript код для автоматического заполнения полей.

## Новый функционал

### 1. Автоматическое заполнение полей с учетом пациента
- **Дозировка**: Автоматически заполняется из `DosingInstruction.dose_description`
- **Частота**: Автоматически заполняется из `DosingInstruction.frequency_description`
- **Путь введения**: Автоматически заполняется из `DosingInstruction.route.name`
- **Длительность**: Автоматически заполняется из `DosingInstruction.duration_description`
- **Инструкции**: Автоматически заполняется из `Regimen.notes`
- **Выбор схемы**: Система автоматически выбирает подходящую схему дозирования на основе возраста и веса пациента

### 2. Уведомления пользователя
- **Успешная загрузка**: Показывается уведомление "Данные о препарате загружены автоматически"
- **Ошибка загрузки**: Показывается предупреждение "Не удалось загрузить данные о препарате"
- **Автоскрытие**: Уведомления автоматически исчезают через 3 секунды

### 3. Очистка полей
- При отмене выбора препарата все поля дозировки автоматически очищаются
- Поле "Путь введения" сбрасывается к значению "oral"

## Логика работы

### 1. Выбор препарата
Когда пользователь выбирает препарат из dropdown:
1. JavaScript отправляет AJAX запрос к `MedicationInfoView`
2. Представление ищет схему применения с инструкциями по дозированию
3. Берется первая доступная инструкция по дозированию
4. Данные возвращаются в формате JSON

### 2. Заполнение полей
JavaScript получает ответ и:
1. Заполняет поля формы полученными данными
2. Показывает уведомление об успешной загрузке
3. Обрабатывает ошибки и показывает предупреждения

### 3. Обработка ошибок
- Если препарат не найден: возвращается 404
- Если нет схем дозирования: поля остаются пустыми
- Если ошибка сервера: возвращается 500 с описанием ошибки

## Преимущества нового подхода

1. **Скорость**: Быстрое заполнение формы без ручного ввода
2. **Точность**: Использование стандартных дозировок из базы данных
3. **Удобство**: Автоматическое заполнение всех полей одним кликом
4. **Гибкость**: Пользователь может изменить автоматически заполненные данные
5. **Информативность**: Уведомления о статусе загрузки данных

## Использование

Теперь пользователь может:

1. **Выбрать препарат**: Выбрать препарат из dropdown в поле "Препарат из справочника"
2. **Автоматическое заполнение**: Все поля дозировки заполняются автоматически с учетом возраста пациента
3. **Проверить данные**: Увидеть уведомление о загрузке данных с названием выбранной схемы
4. **При необходимости изменить**: Отредактировать автоматически заполненные поля
5. **Сохранить**: Добавить препарат в план лечения

### Где работает функционал

Функционал автоматического заполнения полей с учетом пациента работает в следующих местах:

1. **При быстром добавлении из рекомендаций** (`quick_add_medication.html`)
2. **При обычном добавлении препарата в план лечения** (`treatment_medication_form.html`)
3. **При редактировании препарата в плане лечения** (`treatment_medication_form.html`)

## Тестирование

Функционал протестирован:
- ✅ AJAX endpoint работает корректно
- ✅ Данные загружаются из базы данных
- ✅ Поля заполняются автоматически
- ✅ Уведомления отображаются правильно
- ✅ Обработка ошибок работает корректно

## Статус

✅ **РЕАЛИЗОВАНО** - Автоматическое заполнение полей дозировки при выборе препарата добавлено и протестировано. 