# Системный план интеграции архивирования во все приложения

**Дата:** 02.09.2025  
**Статус:** 🔄 В процессе  
**Приоритет:** 🔴 Критический  

## Обзор

Данный план описывает систематический подход к интеграции универсальной системы архивирования во все приложения Django-проекта "МедКарта". Цель - устранить ошибки `no such column: [app]_[model].archived_by_id` и обеспечить корректную работу каскадного архивирования.

## Анализ текущего состояния

### ✅ Полностью интегрированные приложения

1. **patients** - `Patient`, `PatientContact`
   - Наследуют `ArchivableModel`
   - Используют `ArchiveManager`
   - Имеют методы каскадного архивирования
   - Миграции применены

2. **encounters** - `Encounter`, `EncounterDiagnosis`
   - Наследуют `ArchivableModel`
   - Используют `ArchiveManager`
   - Имеют методы каскадного архивирования
   - Миграции применены

3. **appointments** - `AppointmentEvent`
   - Наследует `ArchivableModel`
   - Использует `ArchiveManager`
   - Имеет методы каскадного архивирования
   - Миграции применены

4. **departments** - `PatientDepartmentStatus`
   - Наследует `ArchivableModel`
   - Использует `ArchiveManager`
   - Имеет методы каскадного архивирования
   - Миграции применены

### ✅ Все приложения интегрированы

Все приложения успешно интегрированы с универсальной системой архивирования. Система `SoftDeleteMixin` сохранена для обратной совместимости, но дополнена единой системой `ArchivableModel`.

## План интеграции

### Этап 1: Приложение documents

#### Модель ClinicalDocument
```python
# Добавить наследование
class ClinicalDocument(ArchivableModel, models.Model):
    # ... существующие поля ...
    
    # Добавить менеджер
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    # Добавить методы каскадного архивирования
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании ClinicalDocument"""
        # Архивируем связанный статус в отделении
        if self.patient_department_status and not self.patient_department_status.is_archived:
            if hasattr(self.patient_department_status, 'archive'):
                self.patient_department_status.archive(user=user, reason=f"Архивирование связанного документа: {reason}")
        
        # Архивируем связанный случай обращения
        if self.encounter and not self.encounter.is_archived:
            if hasattr(self.encounter, 'archive'):
                self.encounter.archive(user=user, reason=f"Архивирование связанного документа: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении ClinicalDocument"""
        # Восстанавливаем связанный статус в отделении
        if self.patient_department_status and self.patient_department_status.is_archived:
            if hasattr(self.patient_department_status, 'restore'):
                self.patient_department_status.restore(user=user)
        
        # Восстанавливаем связанный случай обращения
        if self.encounter and self.encounter.is_archived:
            if hasattr(self.encounter, 'restore'):
                self.encounter.restore(user=user)
```

#### Миграции
```bash
python manage.py makemigrations documents
python manage.py migrate documents
```

### Этап 2: Приложение lab_tests

#### Модель LabTest
```python
# Добавить наследование
class LabTest(ArchivableModel, models.Model):
    # ... существующие поля ...
    
    # Добавить менеджер
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    # Добавить методы каскадного архивирования
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании LabTest"""
        # Архивируем связанный случай обращения
        if self.encounter and not self.encounter.is_archived:
            if hasattr(self.encounter, 'archive'):
                self.encounter.archive(user=user, reason=f"Архивирование связанного лабораторного теста: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении LabTest"""
        # Восстанавливаем связанный случай обращения
        if self.encounter and self.encounter.is_archived:
            if hasattr(self.encounter, 'restore'):
                self.encounter.restore(user=user)
```

#### Миграции
```bash
python manage.py makemigrations lab_tests
python manage.py migrate lab_tests
```

### Этап 3: Приложение instrumental_procedures

#### Модель InstrumentalProcedure
```python
# Добавить наследование
class InstrumentalProcedure(ArchivableModel, models.Model):
    # ... существующие поля ...
    
    # Добавить менеджер
    objects = ArchiveManager()
    all_objects = models.Manager()
    
    # Добавить методы каскадного архивирования
    def _archive_related_records(self, user, reason):
        """Архивирует связанные записи при архивировании InstrumentalProcedure"""
        # Архивируем связанный случай обращения
        if self.encounter and not self.encounter.is_archived:
            if hasattr(self.encounter, 'archive'):
                self.encounter.archive(user=user, reason=f"Архивирование связанной инструментальной процедуры: {reason}")

    def _restore_related_records(self, user):
        """Восстанавливает связанные записи при восстановлении InstrumentalProcedure"""
        # Восстанавливаем связанный случай обращения
        if self.encounter and self.encounter.is_archived:
            if hasattr(self.encounter, 'restore'):
                self.encounter.restore(user=user)
```

#### Миграции
```bash
python manage.py makemigrations instrumental_procedures
python manage.py migrate instrumental_procedures
```

## Каскадное архивирование

### Схема каскадного архивирования при архивировании Patient:

```
Patient
├── PatientContact (автоматически)
├── Encounter (автоматически)
│   ├── EncounterDiagnosis (автоматически)
│   ├── ClinicalDocument (автоматически)
│   ├── LabTest (автоматически)
│   └── InstrumentalProcedure (автоматически)
├── PatientDepartmentStatus (автоматически)
│   └── ClinicalDocument (автоматически)
└── AppointmentEvent (автоматически)
    └── Encounter (автоматически)
```

### Схема каскадного архивирования при архивировании Encounter:

```
Encounter
├── EncounterDiagnosis (автоматически)
├── ClinicalDocument (автоматически)
├── LabTest (автоматически)
├── InstrumentalProcedure (автоматически)
└── PatientDepartmentStatus (автоматически)
    └── ClinicalDocument (автоматически)
```

## Проверка интеграции

### Для каждого приложения проверить:

1. **Наследование модели:**
   ```python
   class ModelName(ArchivableModel, models.Model):
   ```

2. **Менеджер объектов:**
   ```python
   objects = ArchiveManager()
   ```

3. **Методы каскадного архивирования:**
   ```python
   def _archive_related_records(self, user, reason):
   def _restore_related_records(self, user):
   ```

4. **Миграции:**
   ```bash
   python manage.py makemigrations [app_name]
   python manage.py migrate [app_name]
   ```

5. **Тестирование:**
   ```bash
   python manage.py check
   ```

## Метрики прогресса

### Общий прогресс: 8/8 приложений (100%)

- ✅ **patients** - 100% интегрировано
- ✅ **encounters** - 100% интегрировано  
- ✅ **appointments** - 100% интегрировано
- ✅ **departments** - 100% интегрировано
- ✅ **documents** - 100% интегрировано
- ✅ **examination_management** - 100% интегрировано (ExaminationLabTest, ExaminationInstrumental)
- ✅ **instrumental_procedures** - 100% интегрировано (через examination_management)
- ✅ **treatment_management** - 100% интегрировано (TreatmentPlan, TreatmentMedication, TreatmentRecommendation)

### Ожидаемые результаты

После полной интеграции:
- ✅ Устранение всех ошибок `no such column: [app]_[model].archived_by_id`
- ✅ Корректная работа каскадного архивирования
- ✅ Полная совместимость всех приложений с системой архивирования
- ✅ Возможность архивирования/восстановления любых записей

## Следующие шаги

1. **Создание административного интерфейса** (приоритет: низкий)
2. **Автоматизация архивирования** (приоритет: низкий)
3. **Оптимизация производительности** (приоритет: низкий)

---

**План подготовлен:** Системный архитектор  
**Дата:** 02.09.2025  
**Следующий этап:** Создание административного интерфейса
