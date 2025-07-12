# Оптимизация архитектуры модуля Encounters

## Анализ текущих проблем

### 1. Нарушение принципа единственной ответственности (SRP)

**Проблема**: Модель `Encounter` содержит слишком много логики
```python
# Текущая реализация - слишком много ответственности
class Encounter(ArchivableModel, models.Model):
    def close_encounter(self, outcome, transfer_department=None):
        # Логика закрытия + создание PatientDepartmentStatus
        # + синхронизация с appointments + валидация документов
    
    def reopen_encounter(self):
        # Логика возврата + отмена PatientDepartmentStatus
        # + синхронизация с appointments
    
    def save(self, *args, **kwargs):
        # Автоматическое управление состоянием + синхронизация
```

**Проблемы**:
- Модель знает о других модулях (departments, appointments)
- Сложная логика в методах модели
- Нарушение принципа инкапсуляции

### 2. Сильная связанность (Tight Coupling)

**Проблема**: Прямые зависимости между модулями
```python
# В модели Encounter
from departments.models import PatientDepartmentStatus, Department
from documents.models import ClinicalDocument

# В views
from departments.models import Department, PatientDepartmentStatus
```

**Проблемы**:
- Изменения в одном модуле влияют на другие
- Сложность тестирования
- Нарушение принципа инверсии зависимостей

### 3. Дублирование логики

**Проблема**: Повторяющаяся логика в разных местах
```python
# В EncounterUpdateView
if old_outcome == 'transferred' and old_transfer_to_department:
    # Логика отмены перевода

# В EncounterCloseView  
if outcome == 'transferred' and transfer_department:
    # Похожая логика создания перевода
```

### 4. Нарушение принципа открытости/закрытости (OCP)

**Проблема**: Сложно добавить новые исходы без изменения существующего кода
```python
OUTCOME_CHOICES = [
    ('consultation_end', 'Консультация'),
    ('transferred', 'Перевод в отделение'),
]
```

### 5. Отсутствие абстракций

**Проблема**: Нет интерфейсов для взаимодействия между модулями
```python
# Прямые вызовы методов других моделей
patient_dept_status.cancel_transfer()
appointment.status = AppointmentStatus.COMPLETED
```

## Предлагаемые оптимизации

### 1. Внедрение Service Layer

**Цель**: Вынести бизнес-логику из моделей в сервисы

```python
# services/encounter_service.py
class EncounterService:
    def __init__(self, encounter):
        self.encounter = encounter
    
    def close_encounter(self, outcome, transfer_department=None):
        """Закрытие случая обращения"""
        # Валидация
        self._validate_documents()
        self._validate_active_state()
        
        # Выполнение операции
        self._set_encounter_data(outcome, transfer_department)
        
        # Синхронизация с другими модулями
        self._sync_with_appointments()
        self._sync_with_departments(transfer_department)
        
        return True
    
    def reopen_encounter(self):
        """Возврат случая в активное состояние"""
        # Логика возврата
        pass
    
    def _validate_documents(self):
        if not self.encounter.documents.exists():
            raise EncounterValidationError("Необходимо прикрепить документы")
    
    def _sync_with_departments(self, department):
        if department:
            DepartmentService.create_transfer(
                patient=self.encounter.patient,
                department=department,
                source_encounter=self.encounter
            )
```

### 2. Создание Event System

**Цель**: Уменьшить связанность через события

```python
# events/encounter_events.py
from django.dispatch import Signal

encounter_closed = Signal()
encounter_reopened = Signal()
encounter_archived = Signal()

# services/encounter_service.py
def close_encounter(self, outcome, transfer_department=None):
    # Основная логика
    self._perform_close(outcome, transfer_department)
    
    # Отправка события
    encounter_closed.send(
        sender=self.__class__,
        encounter=self.encounter,
        outcome=outcome,
        transfer_department=transfer_department
    )

# listeners/encounter_listeners.py
@receiver(encounter_closed)
def handle_encounter_closed(sender, encounter, outcome, transfer_department, **kwargs):
    """Обработчик события закрытия случая"""
    if outcome == 'transferred' and transfer_department:
        DepartmentService.create_transfer(encounter, transfer_department)
    
    AppointmentService.sync_status(encounter)

@receiver(encounter_reopened)
def handle_encounter_reopened(sender, encounter, **kwargs):
    """Обработчик события возврата случая"""
    DepartmentService.cancel_transfer(encounter)
    AppointmentService.sync_status(encounter)
```

### 3. Внедрение Strategy Pattern для исходов

**Цель**: Сделать систему исходов расширяемой

```python
# strategies/outcome_strategies.py
from abc import ABC, abstractmethod

class OutcomeStrategy(ABC):
    @abstractmethod
    def process(self, encounter, **kwargs):
        pass
    
    @abstractmethod
    def validate(self, encounter, **kwargs):
        pass

class ConsultationEndStrategy(OutcomeStrategy):
    def process(self, encounter, **kwargs):
        encounter.outcome = 'consultation_end'
        encounter.date_end = timezone.now()
    
    def validate(self, encounter, **kwargs):
        # Валидация для консультации
        pass

class TransferStrategy(OutcomeStrategy):
    def process(self, encounter, department, **kwargs):
        encounter.outcome = 'transferred'
        encounter.transfer_to_department = department
        encounter.date_end = timezone.now()
    
    def validate(self, encounter, department, **kwargs):
        if not department:
            raise ValidationError("Для перевода необходимо указать отделение")

# services/outcome_service.py
class OutcomeService:
    _strategies = {
        'consultation_end': ConsultationEndStrategy(),
        'transferred': TransferStrategy(),
    }
    
    @classmethod
    def process_outcome(cls, encounter, outcome, **kwargs):
        strategy = cls._strategies.get(outcome)
        if not strategy:
            raise ValueError(f"Неизвестный исход: {outcome}")
        
        strategy.validate(encounter, **kwargs)
        strategy.process(encounter, **kwargs)
```

### 4. Создание Repository Pattern

**Цель**: Абстрагировать доступ к данным

```python
# repositories/encounter_repository.py
class EncounterRepository:
    def get_active_by_patient(self, patient):
        return Encounter.objects.filter(
            patient=patient, 
            is_active=True
        ).select_related('patient', 'doctor')
    
    def get_with_documents(self, encounter_id):
        return Encounter.objects.filter(
            id=encounter_id
        ).prefetch_related('documents').first()
    
    def get_encounter_number(self, encounter):
        return Encounter.objects.filter(
            patient_id=encounter.patient_id,
            date_start__lt=encounter.date_start
        ).count() + 1

# services/encounter_service.py
class EncounterService:
    def __init__(self):
        self.repository = EncounterRepository()
    
    def get_encounter_details(self, encounter_id):
        encounter = self.repository.get_with_documents(encounter_id)
        if not encounter:
            raise EncounterNotFoundError()
        
        return {
            'encounter': encounter,
            'documents': encounter.documents.all(),
            'encounter_number': self.repository.get_encounter_number(encounter)
        }
```

### 5. Внедрение Factory Pattern

**Цель**: Инкапсулировать создание сложных объектов

```python
# factories/encounter_factory.py
class EncounterFactory:
    @staticmethod
    def create_encounter(patient, doctor, date_start=None):
        """Создание нового случая обращения"""
        return Encounter.objects.create(
            patient=patient,
            doctor=doctor,
            date_start=date_start or timezone.now()
        )
    
    @staticmethod
    def create_with_appointment(patient, doctor, appointment):
        """Создание случая с привязкой к записи на прием"""
        encounter = EncounterFactory.create_encounter(patient, doctor)
        appointment.encounter = encounter
        appointment.save()
        return encounter

# services/encounter_service.py
class EncounterService:
    def create_encounter(self, patient, doctor, **kwargs):
        return EncounterFactory.create_encounter(patient, doctor, **kwargs)
```

### 6. Внедрение Command Pattern

**Цель**: Инкапсулировать операции как объекты

```python
# commands/encounter_commands.py
from abc import ABC, abstractmethod

class EncounterCommand(ABC):
    @abstractmethod
    def execute(self):
        pass
    
    @abstractmethod
    def undo(self):
        pass

class CloseEncounterCommand(EncounterCommand):
    def __init__(self, encounter, outcome, transfer_department=None):
        self.encounter = encounter
        self.outcome = outcome
        self.transfer_department = transfer_department
        self.previous_state = None
    
    def execute(self):
        # Сохраняем предыдущее состояние
        self.previous_state = {
            'outcome': self.encounter.outcome,
            'date_end': self.encounter.date_end,
            'transfer_to_department': self.encounter.transfer_to_department,
            'is_active': self.encounter.is_active
        }
        
        # Выполняем операцию
        service = EncounterService(self.encounter)
        return service.close_encounter(self.outcome, self.transfer_department)
    
    def undo(self):
        if self.previous_state:
            for key, value in self.previous_state.items():
                setattr(self.encounter, key, value)
            self.encounter.save()

# services/command_service.py
class CommandService:
    def __init__(self):
        self.command_history = []
    
    def execute_command(self, command):
        result = command.execute()
        self.command_history.append(command)
        return result
    
    def undo_last_command(self):
        if self.command_history:
            command = self.command_history.pop()
            return command.undo()
```

### 7. Внедрение Observer Pattern

**Цель**: Уведомления об изменениях состояния

```python
# observers/encounter_observer.py
class EncounterObserver:
    def __init__(self):
        self.observers = []
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def notify_observers(self, event_type, encounter, **kwargs):
        for observer in self.observers:
            observer.update(event_type, encounter, **kwargs)

class EncounterStateObserver:
    def update(self, event_type, encounter, **kwargs):
        if event_type == 'encounter_closed':
            self._handle_encounter_closed(encounter, **kwargs)
        elif event_type == 'encounter_reopened':
            self._handle_encounter_reopened(encounter, **kwargs)
    
    def _handle_encounter_closed(self, encounter, **kwargs):
        # Логика обработки закрытия
        pass
```

### 8. Оптимизация Views

**Цель**: Упростить представления, вынести логику в сервисы

```python
# views/encounter_views.py
class EncounterCloseView(UpdateView):
    model = Encounter
    form_class = EncounterCloseForm
    template_name = 'encounters/close_form.html'
    
    def form_valid(self, form):
        encounter = self.get_object()
        outcome = form.cleaned_data['outcome']
        transfer_department = form.cleaned_data.get('transfer_to_department')
        
        try:
            # Использование сервиса вместо прямой логики
            service = EncounterService(encounter)
            service.close_encounter(outcome, transfer_department)
            
            messages.success(self.request, "Случай обращения успешно закрыт.")
            return redirect(self.get_success_url())
            
        except EncounterValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
```

### 9. Внедрение CQRS (Command Query Responsibility Segregation)

**Цель**: Разделить операции чтения и записи

```python
# queries/encounter_queries.py
class EncounterQueries:
    def get_encounter_details(self, encounter_id):
        """Чтение деталей случая"""
        return Encounter.objects.select_related(
            'patient', 'doctor', 'transfer_to_department'
        ).prefetch_related('documents').get(id=encounter_id)
    
    def get_patient_encounters(self, patient_id):
        """Чтение всех случаев пациента"""
        return Encounter.objects.filter(
            patient_id=patient_id
        ).select_related('doctor').order_by('-date_start')

# commands/encounter_commands.py
class EncounterCommands:
    def close_encounter(self, encounter_id, outcome, transfer_department=None):
        """Команда закрытия случая"""
        service = EncounterService(Encounter.objects.get(id=encounter_id))
        return service.close_encounter(outcome, transfer_department)
    
    def reopen_encounter(self, encounter_id):
        """Команда возврата случая"""
        service = EncounterService(Encounter.objects.get(id=encounter_id))
        return service.reopen_encounter()
```

### 10. Внедрение Dependency Injection

**Цель**: Уменьшить связанность через инъекцию зависимостей

```python
# containers/service_container.py
class ServiceContainer:
    def __init__(self):
        self._services = {}
    
    def register(self, service_type, implementation):
        self._services[service_type] = implementation
    
    def resolve(self, service_type):
        return self._services[service_type]()

# services/encounter_service.py
class EncounterService:
    def __init__(self, encounter, department_service=None, appointment_service=None):
        self.encounter = encounter
        self.department_service = department_service or DepartmentService()
        self.appointment_service = appointment_service or AppointmentService()
    
    def close_encounter(self, outcome, transfer_department=None):
        # Использование инжектированных сервисов
        if transfer_department:
            self.department_service.create_transfer(
                self.encounter, transfer_department
            )
        
        self.appointment_service.sync_status(self.encounter)
```

## План внедрения оптимизаций

### Этап 1: Создание базовой инфраструктуры
1. Создание папки `services/`
2. Создание базовых сервисов
3. Внедрение Service Layer

### Этап 2: Внедрение Event System
1. Создание системы событий
2. Создание обработчиков событий
3. Рефакторинг существующего кода

### Этап 3: Оптимизация моделей
1. Вынос бизнес-логики из моделей
2. Создание Repository Pattern
3. Внедрение Factory Pattern

### Этап 4: Оптимизация представлений
1. Упрощение views
2. Внедрение CQRS
3. Создание Command Pattern

### Этап 5: Тестирование и документация
1. Создание unit-тестов
2. Обновление документации
3. Проведение code review

## Ожидаемые результаты

### Преимущества после оптимизации:

1. **Улучшенная тестируемость**
   - Изолированные сервисы
   - Mock-объекты для тестирования
   - Четкие интерфейсы

2. **Уменьшенная связанность**
   - События вместо прямых вызовов
   - Инъекция зависимостей
   - Абстракции вместо конкретных реализаций

3. **Повышенная расширяемость**
   - Strategy Pattern для исходов
   - Factory Pattern для создания объектов
   - Command Pattern для операций

4. **Улучшенная производительность**
   - Оптимизированные запросы через Repository
   - Кэширование через Observer Pattern
   - Lazy loading через Service Layer

5. **Упрощенная поддержка**
   - Четкое разделение ответственности
   - Документированные интерфейсы
   - Стандартные паттерны проектирования

## Заключение

Предложенные оптимизации направлены на:
- **Соблюдение принципов SOLID**
- **Уменьшение связанности между модулями**
- **Повышение тестируемости кода**
- **Улучшение расширяемости системы**
- **Упрощение поддержки и развития**

Внедрение этих оптимизаций должно проводиться поэтапно с тщательным тестированием каждого этапа для обеспечения стабильности системы. 