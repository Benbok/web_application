from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Any
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

from ..models import Encounter
from departments.models import PatientDepartmentStatus, Department

User = get_user_model()


class EncounterEvent(ABC):
    """Базовый класс для всех событий encounters"""
    
    def __init__(self, encounter: Encounter, user: User = None, **kwargs):
        self.encounter = encounter
        self.user = user
        self.timestamp = timezone.now()
        self.metadata = kwargs
    
    @abstractmethod
    def get_event_type(self) -> str:
        """Возвращает тип события"""
        pass
    
    def get_description(self) -> str:
        """Возвращает описание события"""
        return f"{self.get_event_type()}: {self.encounter}"


class EncounterClosedEvent(EncounterEvent):
    """Событие закрытия encounter"""
    
    def __init__(self, encounter: Encounter, outcome: str, transfer_department: Department = None, **kwargs):
        super().__init__(encounter, **kwargs)
        self.outcome = outcome
        self.transfer_department = transfer_department
    
    def get_event_type(self) -> str:
        return "encounter_closed"
    
    def get_description(self) -> str:
        base_desc = f"Encounter {self.encounter.id} closed with outcome: {self.outcome}"
        if self.transfer_department:
            base_desc += f" (transferred to {self.transfer_department.name})"
        return base_desc


class EncounterReopenedEvent(EncounterEvent):
    """Событие повторного открытия encounter"""
    
    def get_event_type(self) -> str:
        return "encounter_reopened"
    
    def get_description(self) -> str:
        return f"Encounter {self.encounter.id} reopened"


class EncounterArchivedEvent(EncounterEvent):
    """Событие архивирования encounter"""
    
    def get_event_type(self) -> str:
        return "encounter_archived"
    
    def get_description(self) -> str:
        return f"Encounter {self.encounter.id} archived"


class EncounterUnarchivedEvent(EncounterEvent):
    """Событие разархивирования encounter"""
    
    def get_event_type(self) -> str:
        return "encounter_unarchived"
    
    def get_description(self) -> str:
        return f"Encounter {self.encounter.id} unarchived"


class EventHandler(ABC):
    """Базовый класс для обработчиков событий"""
    
    @abstractmethod
    def handle(self, event: EncounterEvent) -> None:
        """Обрабатывает событие"""
        pass


class LoggingEventHandler(EventHandler):
    """Обработчик событий для логирования"""
    
    def handle(self, event: EncounterEvent) -> None:
        print(f"[{event.timestamp}] {event.get_description()}")
        if event.metadata:
            print(f"Metadata: {event.metadata}")


class PatientDepartmentStatusEventHandler(EventHandler):
    """Обработчик событий для управления статусами пациентов в отделениях"""
    
    def handle(self, event: EncounterEvent) -> None:
        if isinstance(event, EncounterClosedEvent):
            self._handle_encounter_closed(event)
        elif isinstance(event, EncounterReopenedEvent):
            self._handle_encounter_reopened(event)
    
    def _handle_encounter_closed(self, event: EncounterClosedEvent) -> None:
        """Обрабатывает закрытие encounter"""
        if event.outcome == 'transferred' and event.transfer_department:
            # Создаем запись о переводе пациента в отделение
            PatientDepartmentStatus.objects.create(
                patient=event.encounter.patient,
                department=event.transfer_department,
                admission_date=event.encounter.date_end or timezone.now(),
                source_encounter=event.encounter,
                status='pending'
            )
    
    def _handle_encounter_reopened(self, event: EncounterReopenedEvent) -> None:
        """Обрабатывает повторное открытие encounter"""
        # Отменяем перевод, если encounter был закрыт как "переведен"
        if event.encounter.outcome == 'transferred' and event.encounter.transfer_to_department:
            patient_dept_status = PatientDepartmentStatus.objects.filter(
                patient=event.encounter.patient,
                department=event.encounter.transfer_to_department,
                source_encounter=event.encounter
            ).order_by('-admission_date').first()
            
            if patient_dept_status:
                patient_dept_status.cancel_transfer()


class AppointmentSyncEventHandler(EventHandler):
    """Обработчик событий для синхронизации с appointments"""
    
    def handle(self, event: EncounterEvent) -> None:
        if isinstance(event, EncounterClosedEvent):
            self._handle_encounter_closed(event)
        elif isinstance(event, EncounterReopenedEvent):
            self._handle_encounter_reopened(event)
    
    def _handle_encounter_closed(self, event: EncounterClosedEvent) -> None:
        """Синхронизирует статус appointment при закрытии encounter"""
        if hasattr(event.encounter, 'appointment') and event.encounter.appointment:
            from appointments.models import AppointmentStatus
            if event.encounter.appointment.status != AppointmentStatus.COMPLETED:
                event.encounter.appointment.status = AppointmentStatus.COMPLETED
                event.encounter.appointment.save(update_fields=['status'])
    
    def _handle_encounter_reopened(self, event: EncounterReopenedEvent) -> None:
        """Синхронизирует статус appointment при повторном открытии encounter"""
        if hasattr(event.encounter, 'appointment') and event.encounter.appointment:
            from appointments.models import AppointmentStatus
            if event.encounter.appointment.status != AppointmentStatus.SCHEDULED:
                event.encounter.appointment.status = AppointmentStatus.SCHEDULED
                event.encounter.appointment.save(update_fields=['status'])


class EventBus:
    """Центральная шина событий для encounters"""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._register_default_handlers()
        # Интеграция с Observer Pattern
        from ..observers.encounter_observers import observer_manager
        self.observer_manager = observer_manager
    
    def _register_default_handlers(self):
        """Регистрирует обработчики по умолчанию"""
        self.register_handler("encounter_closed", LoggingEventHandler())
        self.register_handler("encounter_closed", PatientDepartmentStatusEventHandler())
        self.register_handler("encounter_closed", AppointmentSyncEventHandler())
        
        self.register_handler("encounter_reopened", LoggingEventHandler())
        self.register_handler("encounter_reopened", PatientDepartmentStatusEventHandler())
        self.register_handler("encounter_reopened", AppointmentSyncEventHandler())
        
        self.register_handler("encounter_archived", LoggingEventHandler())
        self.register_handler("encounter_unarchived", LoggingEventHandler())
    
    def register_handler(self, event_type: str, handler: EventHandler):
        """Регистрирует обработчик для определенного типа событий"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: EncounterEvent):
        """Публикует событие для всех зарегистрированных обработчиков и наблюдателей"""
        event_type = event.get_event_type()
        
        # Обработка через EventHandler
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as e:
                print(f"Error handling event {event_type}: {e}")
        
        # Уведомление наблюдателей
        try:
            self.observer_manager.notify_observers(event)
        except Exception as e:
            print(f"Error notifying observers for event {event_type}: {e}")


# Глобальный экземпляр шины событий
event_bus = EventBus() 