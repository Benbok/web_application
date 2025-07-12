from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any, List

from ..models import Encounter
from ..strategies.outcome_strategies import OutcomeProcessor
from ..commands.encounter_commands import command_invoker, CommandFactory
from ..events.encounter_events import (
    EncounterClosedEvent, 
    EncounterReopenedEvent, 
    EncounterArchivedEvent, 
    EncounterUnarchivedEvent,
    event_bus
)
from departments.models import PatientDepartmentStatus, Department


class EncounterValidationError(Exception):
    """Исключение для ошибок валидации случаев обращения"""
    pass


class EncounterNotFoundError(Exception):
    """Исключение для случая, когда Encounter не найден"""
    pass


class EncounterService:
    """
    Сервис для управления бизнес-логикой случаев обращения.
    Инкапсулирует всю логику работы с Encounter.
    """
    
    def __init__(self, encounter: Encounter):
        self.encounter = encounter
    
    def close_encounter(self, outcome: str, transfer_department: Optional[Department] = None, user=None) -> bool:
        """
        Закрытие случая обращения с указанием исхода.
        
        Args:
            outcome: Исход обращения ('consultation_end' или 'transferred')
            transfer_department: Отделение для перевода (только для 'transferred')
            user: Пользователь, выполняющий операцию
            
        Returns:
            bool: True если случай успешно закрыт, False если уже закрыт
            
        Raises:
            EncounterValidationError: Если нет документов или неверные параметры
        """
        # Создаем команду через Command Pattern
        command = CommandFactory.create_close_command(
            encounter=self.encounter,
            outcome=outcome,
            transfer_department=transfer_department,
            user=user
        )
        
        # Выполняем команду через инвокер
        success = command_invoker.execute_command(command)
        
        if not success:
            raise EncounterValidationError("Невозможно закрыть случай с указанными параметрами.")
        
        return success
    
    def reopen_encounter(self, user=None) -> bool:
        """
        Возврат случая обращения в активное состояние.
        
        Args:
            user: Пользователь, выполняющий операцию
            
        Returns:
            bool: True если случай успешно возвращен, False если уже активен
        """
        # Создаем команду через Command Pattern
        command = CommandFactory.create_reopen_command(
            encounter=self.encounter,
            user=user
        )
        
        # Выполняем команду через инвокер
        success = command_invoker.execute_command(command)
        
        return success
    
    def archive_encounter(self, user=None) -> None:
        """
        Архивирование случая обращения с синхронизацией связанных объектов.
        
        Args:
            user: Пользователь, выполняющий операцию
        """
        # Обнуляем ссылку на Encounter в AppointmentEvent
        self._clear_appointment_reference()
        
        # Архивируем связанные PatientDepartmentStatus
        self._archive_department_transfers()
        
        # Вызываем родительский метод архивирования
        self.encounter.archive()
        
        # Публикуем событие
        event = EncounterArchivedEvent(self.encounter, user=user)
        event_bus.publish(event)
    
    def unarchive_encounter(self, user=None) -> None:
        """
        Восстановление случая обращения из архива.
        
        Args:
            user: Пользователь, выполняющий операцию
        """
        # Восстанавливаем связанные AppointmentEvent
        self._restore_appointment_reference()
        
        # Восстанавливаем связанные PatientDepartmentStatus
        self._restore_department_transfers()
        
        # Вызываем родительский метод восстановления
        self.encounter.unarchive()
        
        # Публикуем событие
        event = EncounterUnarchivedEvent(self.encounter, user=user)
        event_bus.publish(event)
    
    def get_encounter_details(self) -> Dict[str, Any]:
        """
        Получение детальной информации о случае обращения.
        
        Returns:
            Dict с информацией о случае, документах и номере обращения
        """
        return {
            'encounter': self.encounter,
            'documents': self.encounter.documents.all(),
            'encounter_number': self._calculate_encounter_number(),
            'is_active': self.encounter.is_active,
            'has_documents': self.encounter.documents.exists(),
        }
    
    def validate_for_closing(self) -> bool:
        """
        Валидация возможности закрытия случая.
        
        Returns:
            bool: True если случай можно закрыть
        """
        if not self.encounter.is_active:
            return False
        
        if not self.encounter.documents.exists():
            return False
        
        return True
    
    def get_available_outcomes(self) -> Dict[str, str]:
        """
        Получение доступных исходов для случая.
        
        Returns:
            Dict с кодами и названиями исходов
        """
        from ..strategies.outcome_strategies import OutcomeStrategyFactory
        return OutcomeStrategyFactory.get_available_outcomes()
    
    def get_outcome_requirements(self, outcome_code: str) -> Dict[str, list]:
        """
        Получение требований для конкретного исхода.
        
        Args:
            outcome_code: Код исхода
            
        Returns:
            Dict с требованиями для исхода
        """
        outcome_processor = OutcomeProcessor(self.encounter)
        return outcome_processor.get_outcome_requirements(outcome_code)
    
    def undo_last_operation(self) -> bool:
        """
        Отменяет последнюю операцию.
        
        Returns:
            bool: True если операция успешно отменена
        """
        return command_invoker.undo_last_command()
    
    def get_command_history(self) -> List[Dict[str, Any]]:
        """
        Возвращает историю команд.
        
        Returns:
            List с информацией о выполненных командах
        """
        history = []
        for command in command_invoker.get_command_history():
            history.append({
                'description': command.get_description(),
                'executed_at': command.executed_at,
                'execution_successful': command.execution_successful,
                'can_undo': command.can_undo()
            })
        return history
    
    def get_last_command(self) -> Optional[Dict[str, Any]]:
        """
        Возвращает информацию о последней команде.
        
        Returns:
            Dict с информацией о последней команде или None
        """
        last_command = command_invoker.get_last_command()
        if last_command:
            return {
                'description': last_command.get_description(),
                'executed_at': last_command.executed_at,
                'execution_successful': last_command.execution_successful,
                'can_undo': last_command.can_undo()
            }
        return None
    
    # Приватные методы валидации (оставлены для обратной совместимости)
    
    def _validate_documents(self) -> None:
        """Валидация наличия документов"""
        if not self.encounter.documents.exists():
            raise EncounterValidationError(
                "Необходимо прикрепить хотя бы один документ для закрытия случая."
            )
    
    def _validate_active_state(self) -> None:
        """Валидация активного состояния"""
        if not self.encounter.is_active:
            raise EncounterValidationError("Нельзя закрыть уже закрытый случай.")
    
    def _validate_outcome(self, outcome: str, transfer_department: Optional[Department]) -> None:
        """Валидация исхода и отделения"""
        valid_outcomes = ['consultation_end', 'transferred']
        if outcome not in valid_outcomes:
            raise EncounterValidationError(f"Неизвестный исход: {outcome}")
        
        if outcome == 'transferred' and not transfer_department:
            raise EncounterValidationError("Для перевода необходимо указать отделение.")
        
        if outcome != 'transferred' and transfer_department:
            raise EncounterValidationError(
                "Отделение для перевода может быть указано только при исходе 'transferred'."
            )
    
    # Приватные методы выполнения операций (оставлены для обратной совместимости)
    
    def _set_encounter_data(self, outcome: str, transfer_department: Optional[Department]) -> None:
        """Установка данных случая при закрытии (устаревший метод)"""
        # Устанавливаем дату завершения
        if hasattr(self.encounter, 'appointment') and self.encounter.appointment and self.encounter.appointment.end:
            self.encounter.date_end = self.encounter.appointment.end
        else:
            self.encounter.date_end = timezone.now()
        
        # Устанавливаем исход
        self.encounter.outcome = outcome
        
        # Устанавливаем отделение перевода
        if outcome == 'transferred' and transfer_department:
            self.encounter.transfer_to_department = transfer_department
        
        # Сохраняем изменения
        self.encounter.save()
    
    def _clear_encounter_data(self) -> None:
        """Очистка данных случая при возврате"""
        self.encounter.date_end = None
        self.encounter.outcome = None
        self.encounter.transfer_to_department = None
        self.encounter.is_active = True
        self.encounter.save()
    
    # Приватные методы синхронизации
    
    def _sync_with_appointments(self) -> None:
        """Синхронизация с записями на прием"""
        if hasattr(self.encounter, 'appointment') and self.encounter.appointment:
            from appointments.models import AppointmentStatus
            
            appointment = self.encounter.appointment
            if not self.encounter.is_active and appointment.status != AppointmentStatus.COMPLETED:
                appointment.status = AppointmentStatus.COMPLETED
                appointment.save(update_fields=['status'])
            elif self.encounter.is_active and appointment.status != AppointmentStatus.SCHEDULED:
                appointment.status = AppointmentStatus.SCHEDULED
                appointment.save(update_fields=['status'])
    
    def _cancel_department_transfers(self) -> None:
        """Отмена переводов в отделения"""
        if self.encounter.outcome == 'transferred' and self.encounter.transfer_to_department:
            patient_dept_status = PatientDepartmentStatus.objects.filter(
                patient=self.encounter.patient,
                department=self.encounter.transfer_to_department,
                source_encounter=self.encounter
            ).order_by('-admission_date').first()
            
            if patient_dept_status:
                patient_dept_status.cancel_transfer()
    
    def _clear_appointment_reference(self) -> None:
        """Обнуление ссылки на Encounter в AppointmentEvent"""
        appointment = getattr(self.encounter, 'appointment', None)
        if appointment is not None:
            appointment.encounter = None
            appointment.save(update_fields=['encounter'])
    
    def _archive_department_transfers(self) -> None:
        """Архивирование связанных PatientDepartmentStatus"""
        for dept_status in self.encounter.department_transfer_records.all():
            if not getattr(dept_status, 'is_archived', False):
                dept_status.archive()
    
    def _restore_appointment_reference(self) -> None:
        """Восстановление ссылки на Encounter в AppointmentEvent"""
        appointment = getattr(self.encounter, 'appointment', None)
        if appointment is not None and getattr(appointment, 'is_archived', False):
            appointment.unarchive()
    
    def _restore_department_transfers(self) -> None:
        """Восстановление связанных PatientDepartmentStatus"""
        for dept_status in PatientDepartmentStatus.all_objects.filter(source_encounter=self.encounter):
            if getattr(dept_status, 'is_archived', False):
                dept_status.unarchive()
    
    # Приватные методы вычислений
    
    def _calculate_encounter_number(self) -> int:
        """Вычисление номера обращения для пациента"""
        return Encounter.objects.filter(
            patient_id=self.encounter.patient_id,
            date_start__lt=self.encounter.date_start
        ).count() + 1 