"""
Примеры использования оптимизированной архитектуры модуля encounters.

Этот файл демонстрирует, как использовать новые сервисы, репозитории и фабрики
для работы с случаями обращения.
"""

from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import Encounter
from ..services.encounter_service import EncounterService, EncounterValidationError
from ..repositories.encounter_repository import EncounterRepository
from ..factories.encounter_factory import EncounterFactory
from ..strategies.outcome_strategies import OutcomeStrategyFactory, OutcomeProcessor
from ..commands.encounter_commands import command_invoker, CommandFactory
from ..events.encounter_events import event_bus
from ..observers.encounter_observers import observer_manager
from patients.models import Patient
from departments.models import Department

User = get_user_model()


def example_basic_encounter_operations():
    """
    Пример базовых операций с случаями обращения.
    """
    print("=== Базовые операции с случаями обращения ===")
    
    # Получаем тестовые данные
    patient = Patient.objects.first()
    doctor = User.objects.first()
    department = Department.objects.first()
    
    if not all([patient, doctor, department]):
        print("Недостаточно данных для демонстрации")
        return
    
    # 1. Создание случая обращения с использованием фабрики
    print("\n1. Создание случая обращения:")
    encounter = EncounterFactory.create_encounter(
        patient=patient,
        doctor=doctor,
        date_start=timezone.now()
    )
    print(f"Создан случай обращения: {encounter}")
    
    # 2. Использование сервиса для получения деталей
    print("\n2. Получение деталей случая:")
    service = EncounterService(encounter)
    details = service.get_encounter_details()
    print(f"Детали: {details}")
    
    # 3. Закрытие случая обращения
    print("\n3. Закрытие случая обращения:")
    try:
        # Сначала нужно добавить документы
        from documents.models import ClinicalDocument, DocumentType
        document_type = DocumentType.objects.first()
        if document_type:
            ClinicalDocument.objects.create(
                content_type=encounter.get_content_type(),
                object_id=encounter.id,
                document_type=document_type,
                data={'symptoms': 'Головная боль'}
            )
        
        # Теперь можно закрыть
        service.close_encounter('consultation_end')
        print("Случай успешно закрыт")
        
    except EncounterValidationError as e:
        print(f"Ошибка валидации: {e}")
    
    # 4. Возврат случая в активное состояние
    print("\n4. Возврат случая в активное состояние:")
    if service.reopen_encounter():
        print("Случай возвращен в активное состояние")
    else:
        print("Не удалось вернуть случай")


def example_repository_operations():
    """
    Пример использования репозитория для работы с данными.
    """
    print("\n=== Операции с репозиторием ===")
    
    repository = EncounterRepository()
    
    # 1. Получение статистики
    print("\n1. Статистика случаев обращения:")
    stats = repository.get_encounters_statistics()
    print(f"Всего случаев: {stats['total']}")
    print(f"Активных: {stats['active']}")
    print(f"Закрытых: {stats['closed']}")
    print(f"Консультаций: {stats['consultation_end']}")
    print(f"Переводов: {stats['transferred']}")
    
    # 2. Получение случаев по пациенту
    patient = Patient.objects.first()
    if patient:
        print(f"\n2. Случаи пациента {patient.full_name}:")
        encounters = repository.get_by_patient(patient)
        for encounter in encounters[:5]:  # Показываем первые 5
            print(f"- {encounter}")
    
    # 3. Получение активных случаев
    print("\n3. Активные случаи обращения:")
    active_encounters = repository.get_active_encounters_count()
    print(f"Количество активных случаев: {active_encounters}")
    
    # 4. Получение случаев с документами
    print("\n4. Случаи с документами:")
    encounters_with_docs = repository.get_encounters_with_documents()
    print(f"Количество случаев с документами: {encounters_with_docs.count()}")


def example_factory_operations():
    """
    Пример использования фабрики для создания различных типов случаев обращения.
    """
    print("\n=== Операции с фабрикой ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    department = Department.objects.first()
    
    if not all([patient, doctor, department]):
        print("Недостаточно данных для демонстрации")
        return
    
    # 1. Создание базового случая
    print("\n1. Создание базового случая:")
    basic_encounter = EncounterFactory.create_encounter(
        patient=patient,
        doctor=doctor
    )
    print(f"Создан базовый случай: {basic_encounter}")
    
    # 2. Создание случая с переводом
    print("\n2. Создание случая с переводом:")
    transfer_encounter = EncounterFactory.create_transfer_encounter(
        patient=patient,
        doctor=doctor,
        transfer_department=department
    )
    print(f"Создан случай с переводом: {transfer_encounter}")
    
    # 3. Создание случая с завершением консультации
    print("\n3. Создание случая с завершением консультации:")
    consultation_encounter = EncounterFactory.create_consultation_encounter(
        patient=patient,
        doctor=doctor
    )
    print(f"Создан случай с завершением консультации: {consultation_encounter}")
    
    # 4. Создание архивированного случая
    print("\n4. Создание архивированного случая:")
    archived_encounter = EncounterFactory.create_archived_encounter(
        patient=patient,
        doctor=doctor
    )
    print(f"Создан архивированный случай: {archived_encounter}")
    
    # 5. Создание тестового случая
    print("\n5. Создание тестового случая:")
    test_encounter = EncounterFactory.create_test_encounter()
    print(f"Создан тестовый случай: {test_encounter}")


def example_service_operations():
    """
    Пример использования сервиса для сложных операций.
    """
    print("\n=== Операции с сервисом ===")
    
    # Получаем активный случай обращения
    repository = EncounterRepository()
    encounter = repository.get_active_by_id(1)  # Предполагаем, что есть случай с ID=1
    
    if not encounter:
        print("Активный случай обращения не найден")
        return
    
    service = EncounterService(encounter)
    
    # 1. Валидация возможности закрытия
    print("\n1. Валидация возможности закрытия:")
    can_close = service.validate_for_closing()
    print(f"Можно закрыть: {can_close}")
    
    # 2. Получение деталей
    print("\n2. Получение деталей:")
    details = service.get_encounter_details()
    print(f"Номер обращения: {details['encounter_number']}")
    print(f"Активен: {details['is_active']}")
    print(f"Есть документы: {details['has_documents']}")
    print(f"Количество документов: {details['documents'].count()}")
    
    # 3. Архивирование
    print("\n3. Архивирование:")
    try:
        service.archive_encounter()
        print("Случай успешно архивирован")
    except Exception as e:
        print(f"Ошибка при архивировании: {e}")
    
    # 4. Восстановление из архива
    print("\n4. Восстановление из архива:")
    try:
        service.unarchive_encounter()
        print("Случай успешно восстановлен")
    except Exception as e:
        print(f"Ошибка при восстановлении: {e}")


def example_complex_scenarios():
    """
    Примеры сложных сценариев использования.
    """
    print("\n=== Сложные сценарии ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    department = Department.objects.first()
    
    if not all([patient, doctor, department]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Сценарий 1: Полный жизненный цикл случая обращения
    print("\nСценарий 1: Полный жизненный цикл случая обращения")
    
    # Создание
    encounter = EncounterFactory.create_encounter(patient, doctor)
    print(f"1. Создан случай: {encounter}")
    
    # Добавление документов
    from documents.models import ClinicalDocument, DocumentType
    document_type = DocumentType.objects.first()
    if document_type:
        ClinicalDocument.objects.create(
            content_type=encounter.get_content_type(),
            object_id=encounter.id,
            document_type=document_type,
            data={'symptoms': 'Головная боль', 'diagnosis': 'Мигрень'}
        )
        print("2. Добавлен документ")
    
    # Закрытие с переводом
    service = EncounterService(encounter)
    try:
        service.close_encounter('transferred', department)
        print("3. Случай закрыт с переводом")
    except EncounterValidationError as e:
        print(f"Ошибка при закрытии: {e}")
    
    # Возврат в активное состояние
    if service.reopen_encounter():
        print("4. Случай возвращен в активное состояние")
    
    # Архивирование
    service.archive_encounter()
    print("5. Случай архивирован")
    
    # Восстановление из архива
    service.unarchive_encounter()
    print("6. Случай восстановлен из архива")
    
    # Сценарий 2: Массовые операции
    print("\nСценарий 2: Массовые операции")
    
    # Создание нескольких случаев
    patients = Patient.objects.all()[:3]  # Берем первых 3 пациентов
    encounters = EncounterFactory.create_encounter_batch(
        patients=patients,
        doctor=doctor
    )
    print(f"Создано {len(encounters)} случаев обращения")
    
    # Получение статистики
    repository = EncounterRepository()
    stats = repository.get_encounters_statistics()
    print(f"Общая статистика: {stats}")


def example_error_handling():
    """
    Примеры обработки ошибок.
    """
    print("\n=== Обработка ошибок ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    
    if not all([patient, doctor]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Создаем случай без документов
    encounter = EncounterFactory.create_encounter(patient, doctor)
    service = EncounterService(encounter)
    
    # Попытка закрыть без документов
    print("\n1. Попытка закрыть случай без документов:")
    try:
        service.close_encounter('consultation_end')
        print("Случай закрыт успешно")
    except EncounterValidationError as e:
        print(f"Ошибка валидации: {e}")
    
    # Попытка закрыть уже закрытый случай
    print("\n2. Попытка закрыть уже закрытый случай:")
    try:
        service.close_encounter('consultation_end')
        print("Случай закрыт успешно")
    except EncounterValidationError as e:
        print(f"Ошибка валидации: {e}")
    
    # Попытка вернуть активный случай
    print("\n3. Попытка вернуть активный случай:")
    if service.reopen_encounter():
        print("Случай возвращен успешно")
    else:
        print("Случай уже активен")


def example_strategy_pattern():
    """
    Примеры использования Strategy Pattern для исходов.
    """
    print("\n=== Strategy Pattern для исходов ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    department = Department.objects.first()
    
    if not all([patient, doctor, department]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Создаем случай обращения
    encounter = EncounterFactory.create_encounter(patient, doctor)
    
    # 1. Получение доступных исходов
    print("\n1. Доступные исходы:")
    available_outcomes = OutcomeStrategyFactory.get_available_outcomes()
    for code, display_name in available_outcomes.items():
        print(f"- {code}: {display_name}")
    
    # 2. Получение требований для каждого исхода
    print("\n2. Требования для исходов:")
    outcome_processor = OutcomeProcessor(encounter)
    for outcome_code in available_outcomes.keys():
        requirements = outcome_processor.get_outcome_requirements(outcome_code)
        print(f"\n{outcome_code}:")
        print(f"  Обязательные поля: {requirements['required_fields']}")
        print(f"  Опциональные поля: {requirements['optional_fields']}")
        print(f"  Отображаемое название: {requirements['display_name']}")
    
    # 3. Валидация исходов
    print("\n3. Валидация исходов:")
    
    # Добавляем документ для возможности закрытия
    from documents.models import ClinicalDocument, DocumentType
    document_type = DocumentType.objects.first()
    if document_type:
        ClinicalDocument.objects.create(
            content_type=encounter.get_content_type(),
            object_id=encounter.id,
            document_type=document_type,
            data={'symptoms': 'Головная боль'}
        )
    
    # Проверяем валидность каждого исхода
    for outcome_code in available_outcomes.keys():
        is_valid = outcome_processor.validate_outcome(outcome_code, transfer_department=department)
        print(f"{outcome_code}: {'Валиден' if is_valid else 'Невалиден'}")
    
    # 4. Обработка исхода через стратегию
    print("\n4. Обработка исхода через стратегию:")
    try:
        success = outcome_processor.process_outcome(
            'consultation_end',
            user=doctor
        )
        print(f"Результат обработки: {'Успешно' if success else 'Неуспешно'}")
    except Exception as e:
        print(f"Ошибка при обработке: {e}")


def example_event_system():
    """
    Примеры использования Event System.
    """
    print("\n=== Event System ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    department = Department.objects.first()
    
    if not all([patient, doctor, department]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Создаем случай обращения
    encounter = EncounterFactory.create_encounter(patient, doctor)
    
    # 1. Регистрация пользовательского обработчика событий
    print("\n1. Регистрация пользовательского обработчика:")
    
    class CustomEventHandler:
        def handle(self, event):
            print(f"Пользовательский обработчик: {event.get_description()}")
    
    # Регистрируем обработчик для событий закрытия
    event_bus.register_handler("encounter_closed", CustomEventHandler())
    
    # 2. Закрытие случая с публикацией события
    print("\n2. Закрытие случая с событием:")
    
    # Добавляем документ
    from documents.models import ClinicalDocument, DocumentType
    document_type = DocumentType.objects.first()
    if document_type:
        ClinicalDocument.objects.create(
            content_type=encounter.get_content_type(),
            object_id=encounter.id,
            document_type=document_type,
            data={'symptoms': 'Головная боль'}
        )
    
    # Закрываем случай (событие будет опубликовано автоматически)
    service = EncounterService(encounter)
    try:
        service.close_encounter('consultation_end', user=doctor)
        print("Случай закрыт, событие опубликовано")
    except Exception as e:
        print(f"Ошибка при закрытии: {e}")
    
    # 3. Возврат случая с событием
    print("\n3. Возврат случая с событием:")
    if service.reopen_encounter(user=doctor):
        print("Случай возвращен, событие опубликовано")
    
    # 4. Архивирование с событием
    print("\n4. Архивирование с событием:")
    service.archive_encounter(user=doctor)
    print("Случай архивирован, событие опубликовано")
    
    # 5. Восстановление из архива с событием
    print("\n5. Восстановление из архива с событием:")
    service.unarchive_encounter(user=doctor)
    print("Случай восстановлен, событие опубликовано")


def example_advanced_service_features():
    """
    Примеры использования расширенных возможностей сервиса.
    """
    print("\n=== Расширенные возможности сервиса ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    
    if not all([patient, doctor]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Создаем случай обращения
    encounter = EncounterFactory.create_encounter(patient, doctor)
    service = EncounterService(encounter)
    
    # 1. Получение доступных исходов через сервис
    print("\n1. Доступные исходы через сервис:")
    available_outcomes = service.get_available_outcomes()
    for code, display_name in available_outcomes.items():
        print(f"- {code}: {display_name}")
    
    # 2. Получение требований для конкретного исхода
    print("\n2. Требования для исхода 'consultation_end':")
    requirements = service.get_outcome_requirements('consultation_end')
    print(f"Обязательные поля: {requirements['required_fields']}")
    print(f"Опциональные поля: {requirements['optional_fields']}")
    print(f"Отображаемое название: {requirements['display_name']}")
    
    # 3. Закрытие с пользователем
    print("\n3. Закрытие с указанием пользователя:")
    
    # Добавляем документ
    from documents.models import ClinicalDocument, DocumentType
    document_type = DocumentType.objects.first()
    if document_type:
        ClinicalDocument.objects.create(
            content_type=encounter.get_content_type(),
            object_id=encounter.id,
            document_type=document_type,
            data={'symptoms': 'Головная боль'}
        )
    
    try:
        service.close_encounter('consultation_end', user=doctor)
        print("Случай закрыт с указанием пользователя")
    except Exception as e:
        print(f"Ошибка при закрытии: {e}")


def example_command_pattern():
    """
    Примеры использования Command Pattern.
    """
    print("\n=== Command Pattern ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    department = Department.objects.first()
    
    if not all([patient, doctor, department]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Создаем случай обращения
    encounter = EncounterFactory.create_encounter(patient, doctor)
    service = EncounterService(encounter)
    
    # 1. Создание команды закрытия
    print("\n1. Создание команды закрытия:")
    close_command = CommandFactory.create_close_command(
        encounter=encounter,
        outcome='consultation_end',
        user=doctor
    )
    print(f"Команда создана: {close_command.get_description()}")
    
    # 2. Выполнение команды через инвокер
    print("\n2. Выполнение команды:")
    
    # Добавляем документ для возможности закрытия
    from documents.models import ClinicalDocument, DocumentType
    document_type = DocumentType.objects.first()
    if document_type:
        ClinicalDocument.objects.create(
            content_type=encounter.get_content_type(),
            object_id=encounter.id,
            document_type=document_type,
            data={'symptoms': 'Головная боль'}
        )
    
    success = command_invoker.execute_command(close_command)
    print(f"Команда выполнена: {'Успешно' if success else 'Неуспешно'}")
    
    # 3. Отмена последней команды
    print("\n3. Отмена последней команды:")
    undo_success = command_invoker.undo_last_command()
    print(f"Команда отменена: {'Успешно' if undo_success else 'Неуспешно'}")
    
    # 4. История команд
    print("\n4. История команд:")
    history = command_invoker.get_command_history()
    for i, command in enumerate(history, 1):
        print(f"{i}. {command.get_description()} - {'Выполнена' if command.execution_successful else 'Не выполнена'}")
    
    # 5. Работа с командами через сервис
    print("\n5. Работа с командами через сервис:")
    
    # Закрываем случай
    service.close_encounter('consultation_end', user=doctor)
    
    # Получаем историю команд
    command_history = service.get_command_history()
    print(f"Количество команд в истории: {len(command_history)}")
    
    # Получаем информацию о последней команде
    last_command = service.get_last_command()
    if last_command:
        print(f"Последняя команда: {last_command['description']}")
        print(f"Можно отменить: {last_command['can_undo']}")
    
    # Отменяем последнюю операцию
    undo_result = service.undo_last_operation()
    print(f"Операция отменена: {'Успешно' if undo_result else 'Неуспешно'}")


def example_observer_pattern():
    """
    Примеры использования Observer Pattern.
    """
    print("\n=== Observer Pattern ===")
    
    patient = Patient.objects.first()
    doctor = User.objects.first()
    
    if not all([patient, doctor]):
        print("Недостаточно данных для демонстрации")
        return
    
    # Создаем случай обращения
    encounter = EncounterFactory.create_encounter(patient, doctor)
    service = EncounterService(encounter)
    
    # 1. Регистрация пользовательского наблюдателя
    print("\n1. Регистрация пользовательского наблюдателя:")
    
    class CustomObserver:
        def __init__(self):
            self.name = "CustomObserver"
            self.observations_count = 0
        
        def update(self, event):
            print(f"Пользовательский наблюдатель: {event.get_description()}")
            self.observations_count += 1
        
        def get_name(self):
            return self.name
        
        def get_observations_count(self):
            return self.observations_count
    
    custom_observer = CustomObserver()
    observer_manager.register_observer('custom', custom_observer)
    
    # 2. Получение статистики наблюдателей
    print("\n2. Статистика наблюдателей:")
    stats = observer_manager.get_observer_stats()
    for name, stat in stats.items():
        print(f"{name}: {stat['observations_count']} наблюдений")
    
    # 3. Выполнение операций с автоматическим уведомлением наблюдателей
    print("\n3. Выполнение операций:")
    
    # Добавляем документ
    from documents.models import ClinicalDocument, DocumentType
    document_type = DocumentType.objects.first()
    if document_type:
        ClinicalDocument.objects.create(
            content_type=encounter.get_content_type(),
            object_id=encounter.id,
            document_type=document_type,
            data={'symptoms': 'Головная боль'}
        )
    
    # Закрываем случай (наблюдатели уведомляются автоматически)
    service.close_encounter('consultation_end', user=doctor)
    
    # Возвращаем случай (наблюдатели уведомляются автоматически)
    service.reopen_encounter(user=doctor)
    
    # 4. Получение метрик от наблюдателей
    print("\n4. Метрики от наблюдателей:")
    
    # Метрики
    metrics_observer = observer_manager.get_observer('metrics')
    if metrics_observer:
        metrics = metrics_observer.get_metrics()
        print(f"Всего событий: {metrics['total_events']}")
        print(f"События по типам: {metrics['events_by_type']}")
    
    # Производительность
    performance_observer = observer_manager.get_observer('performance')
    if performance_observer:
        performance_metrics = performance_observer.get_performance_metrics()
        print(f"Среднее время обработки: {performance_metrics['average_processing_time']:.4f} сек")
    
    # 5. Отмена регистрации наблюдателя
    print("\n5. Отмена регистрации наблюдателя:")
    observer_manager.unregister_observer('custom')
    print("Пользовательский наблюдатель отменен")


def run_all_examples():
    """
    Запуск всех примеров.
    """
    print("Демонстрация оптимизированной архитектуры модуля encounters")
    print("=" * 60)
    
    try:
        example_basic_encounter_operations()
        example_repository_operations()
        example_factory_operations()
        example_service_operations()
        example_complex_scenarios()
        example_error_handling()
        example_strategy_pattern()
        example_event_system()
        example_advanced_service_features()
        example_command_pattern()
        example_observer_pattern()
        
        print("\n" + "=" * 60)
        print("Демонстрация завершена успешно!")
        
    except Exception as e:
        print(f"\nОшибка при выполнении примеров: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Этот код можно запустить для демонстрации
    # python -m encounters.examples.usage_examples
    run_all_examples() 