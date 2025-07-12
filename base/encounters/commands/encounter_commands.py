from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

from ..models import Encounter
from ..events.encounter_events import event_bus, EncounterClosedEvent, EncounterReopenedEvent
from departments.models import Department

User = get_user_model()


class Command(ABC):
    """Базовый класс для всех команд"""
    
    def __init__(self, encounter: Encounter, user: User = None):
        self.encounter = encounter
        self.user = user
        self.executed_at = None
        self.execution_successful = False
    
    @abstractmethod
    def execute(self) -> bool:
        """Выполняет команду"""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Отменяет команду"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Возвращает описание команды"""
        pass
    
    def can_execute(self) -> bool:
        """Проверяет, можно ли выполнить команду"""
        return True
    
    def can_undo(self) -> bool:
        """Проверяет, можно ли отменить команду"""
        return self.execution_successful and self.executed_at is not None


class CloseEncounterCommand(Command):
    """Команда для закрытия случая обращения"""
    
    def __init__(self, encounter: Encounter, outcome: str, transfer_department: Department = None, user: User = None):
        super().__init__(encounter, user)
        self.outcome = outcome
        self.transfer_department = transfer_department
        self.previous_state = None
    
    def get_description(self) -> str:
        return f"Закрытие случая {self.encounter.id} с исходом '{self.outcome}'"
    
    def can_execute(self) -> bool:
        """Проверяет возможность закрытия"""
        if not self.encounter.is_active:
            return False
        
        if not self.encounter.documents.exists():
            return False
        
        if self.outcome == 'transferred' and not self.transfer_department:
            return False
        
        return True
    
    def execute(self) -> bool:
        """Выполняет закрытие случая"""
        if not self.can_execute():
            return False
        
        # Сохраняем предыдущее состояние
        self.previous_state = {
            'is_active': self.encounter.is_active,
            'outcome': self.encounter.outcome,
            'transfer_to_department': self.encounter.transfer_to_department,
            'date_end': self.encounter.date_end
        }
        
        try:
            with transaction.atomic():
                # Устанавливаем дату завершения
                if hasattr(self.encounter, 'appointment') and self.encounter.appointment and self.encounter.appointment.end:
                    self.encounter.date_end = self.encounter.appointment.end
                else:
                    self.encounter.date_end = timezone.now()
                
                # Устанавливаем исход
                self.encounter.outcome = self.outcome
                
                # Устанавливаем отделение перевода
                if self.outcome == 'transferred' and self.transfer_department:
                    self.encounter.transfer_to_department = self.transfer_department
                
                # Сохраняем изменения
                self.encounter.save()
                
                # Публикуем событие
                event = EncounterClosedEvent(
                    encounter=self.encounter,
                    outcome=self.outcome,
                    transfer_department=self.transfer_department,
                    user=self.user
                )
                event_bus.publish(event)
                
                self.executed_at = timezone.now()
                self.execution_successful = True
                return True
                
        except Exception as e:
            print(f"Ошибка при выполнении команды закрытия: {e}")
            return False
    
    def undo(self) -> bool:
        """Отменяет закрытие случая"""
        if not self.can_undo() or not self.previous_state:
            return False
        
        try:
            with transaction.atomic():
                # Восстанавливаем предыдущее состояние
                self.encounter.is_active = self.previous_state['is_active']
                self.encounter.outcome = self.previous_state['outcome']
                self.encounter.transfer_to_department = self.previous_state['transfer_to_department']
                self.encounter.date_end = self.previous_state['date_end']
                
                # Сохраняем изменения
                self.encounter.save()
                
                # Публикуем событие возврата
                event = EncounterReopenedEvent(self.encounter, user=self.user)
                event_bus.publish(event)
                
                return True
                
        except Exception as e:
            print(f"Ошибка при отмене команды закрытия: {e}")
            return False


class ReopenEncounterCommand(Command):
    """Команда для возврата случая обращения в активное состояние"""
    
    def __init__(self, encounter: Encounter, user: User = None):
        super().__init__(encounter, user)
        self.previous_state = None
    
    def get_description(self) -> str:
        return f"Возврат случая {self.encounter.id} в активное состояние"
    
    def can_execute(self) -> bool:
        """Проверяет возможность возврата"""
        return not self.encounter.is_active
    
    def execute(self) -> bool:
        """Выполняет возврат случая"""
        if not self.can_execute():
            return False
        
        # Сохраняем предыдущее состояние
        self.previous_state = {
            'is_active': self.encounter.is_active,
            'outcome': self.encounter.outcome,
            'transfer_to_department': self.encounter.transfer_to_department,
            'date_end': self.encounter.date_end
        }
        
        try:
            with transaction.atomic():
                # Отменяем переводы в отделения
                if self.encounter.outcome == 'transferred' and self.encounter.transfer_to_department:
                    from departments.models import PatientDepartmentStatus
                    patient_dept_status = PatientDepartmentStatus.objects.filter(
                        patient=self.encounter.patient,
                        department=self.encounter.transfer_to_department,
                        source_encounter=self.encounter
                    ).order_by('-admission_date').first()
                    
                    if patient_dept_status:
                        patient_dept_status.cancel_transfer()
                
                # Очищаем данные случая
                self.encounter.date_end = None
                self.encounter.outcome = None
                self.encounter.transfer_to_department = None
                self.encounter.is_active = True
                
                # Сохраняем изменения
                self.encounter.save()
                
                # Публикуем событие
                event = EncounterReopenedEvent(self.encounter, user=self.user)
                event_bus.publish(event)
                
                self.executed_at = timezone.now()
                self.execution_successful = True
                return True
                
        except Exception as e:
            print(f"Ошибка при выполнении команды возврата: {e}")
            return False
    
    def undo(self) -> bool:
        """Отменяет возврат случая"""
        if not self.can_undo() or not self.previous_state:
            return False
        
        try:
            with transaction.atomic():
                # Восстанавливаем предыдущее состояние
                self.encounter.is_active = self.previous_state['is_active']
                self.encounter.outcome = self.previous_state['outcome']
                self.encounter.transfer_to_department = self.previous_state['transfer_to_department']
                self.encounter.date_end = self.previous_state['date_end']
                
                # Сохраняем изменения
                self.encounter.save()
                
                # Публикуем событие закрытия
                event = EncounterClosedEvent(
                    encounter=self.encounter,
                    outcome=self.encounter.outcome,
                    transfer_department=self.encounter.transfer_to_department,
                    user=self.user
                )
                event_bus.publish(event)
                
                return True
                
        except Exception as e:
            print(f"Ошибка при отмене команды возврата: {e}")
            return False


class CommandInvoker:
    """Инвокер для выполнения команд"""
    
    def __init__(self):
        self.command_history: List[Command] = []
        self.max_history_size = 100
    
    def execute_command(self, command: Command) -> bool:
        """Выполняет команду и сохраняет в истории"""
        if not command.can_execute():
            print(f"Команда не может быть выполнена: {command.get_description()}")
            return False
        
        success = command.execute()
        
        if success:
            self.command_history.append(command)
            
            # Ограничиваем размер истории
            if len(self.command_history) > self.max_history_size:
                self.command_history.pop(0)
        
        return success
    
    def undo_last_command(self) -> bool:
        """Отменяет последнюю команду"""
        if not self.command_history:
            print("История команд пуста")
            return False
        
        last_command = self.command_history.pop()
        
        if not last_command.can_undo():
            print(f"Команда не может быть отменена: {last_command.get_description()}")
            return False
        
        success = last_command.undo()
        
        if success:
            print(f"Команда отменена: {last_command.get_description()}")
        else:
            print(f"Ошибка при отмене команды: {last_command.get_description()}")
        
        return success
    
    def get_command_history(self) -> List[Command]:
        """Возвращает историю команд"""
        return self.command_history.copy()
    
    def clear_history(self):
        """Очищает историю команд"""
        self.command_history.clear()
    
    def get_last_command(self) -> Optional[Command]:
        """Возвращает последнюю команду"""
        return self.command_history[-1] if self.command_history else None


class CommandFactory:
    """Фабрика для создания команд"""
    
    @staticmethod
    def create_close_command(encounter: Encounter, outcome: str, transfer_department: Department = None, user: User = None) -> CloseEncounterCommand:
        """Создает команду закрытия случая"""
        return CloseEncounterCommand(encounter, outcome, transfer_department, user)
    
    @staticmethod
    def create_reopen_command(encounter: Encounter, user: User = None) -> ReopenEncounterCommand:
        """Создает команду возврата случая"""
        return ReopenEncounterCommand(encounter, user)


# Глобальный инвокер для приложения
command_invoker = CommandInvoker() 