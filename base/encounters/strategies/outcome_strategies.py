from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import Encounter
from departments.models import Department
from ..events.encounter_events import EncounterClosedEvent, event_bus


class OutcomeStrategy(ABC):
    """Базовый класс для стратегий обработки исходов encounters"""
    
    def __init__(self, encounter: Encounter):
        self.encounter = encounter
    
    @abstractmethod
    def get_outcome_code(self) -> str:
        """Возвращает код исхода"""
        pass
    
    @abstractmethod
    def get_outcome_display(self) -> str:
        """Возвращает отображаемое название исхода"""
        pass
    
    @abstractmethod
    def validate(self, **kwargs) -> bool:
        """Валидирует параметры для данного исхода"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> bool:
        """Выполняет логику для данного исхода"""
        pass
    
    def get_required_fields(self) -> list:
        """Возвращает список обязательных полей для данного исхода"""
        return []
    
    def get_optional_fields(self) -> list:
        """Возвращает список опциональных полей для данного исхода"""
        return []


class ConsultationEndStrategy(OutcomeStrategy):
    """Стратегия для завершения консультации"""
    
    def get_outcome_code(self) -> str:
        return 'consultation_end'
    
    def get_outcome_display(self) -> str:
        return 'Консультация'
    
    def validate(self, **kwargs) -> bool:
        """Проверяет, что есть документы для закрытия"""
        if not self.encounter.documents.exists():
            return False
        return True
    
    def execute(self, **kwargs) -> bool:
        """Выполняет закрытие консультации"""
        if not self.validate(**kwargs):
            return False
        
        with transaction.atomic():
            # Устанавливаем дату окончания
            if hasattr(self.encounter, 'appointment') and self.encounter.appointment and self.encounter.appointment.end:
                self.encounter.date_end = self.encounter.appointment.end
            else:
                self.encounter.date_end = timezone.now()
            
            # Устанавливаем исход
            self.encounter.outcome = self.get_outcome_code()
            self.encounter.transfer_to_department = None
            self.encounter.save()
            
            # Публикуем событие
            event = EncounterClosedEvent(
                encounter=self.encounter,
                outcome=self.get_outcome_code(),
                user=kwargs.get('user')
            )
            event_bus.publish(event)
            
            return True
    
    def get_required_fields(self) -> list:
        return ['documents']


class TransferStrategy(OutcomeStrategy):
    """Стратегия для перевода в отделение"""
    
    def get_outcome_code(self) -> str:
        return 'transferred'
    
    def get_outcome_display(self) -> str:
        return 'Перевод в отделение'
    
    def validate(self, **kwargs) -> bool:
        """Проверяет наличие документов и отделения для перевода"""
        if not self.encounter.documents.exists():
            return False
        
        transfer_department = kwargs.get('transfer_department')
        if not transfer_department:
            return False
        
        return True
    
    def execute(self, **kwargs) -> bool:
        """Выполняет перевод в отделение"""
        if not self.validate(**kwargs):
            return False
        
        transfer_department = kwargs.get('transfer_department')
        
        with transaction.atomic():
            # Устанавливаем дату окончания
            if hasattr(self.encounter, 'appointment') and self.encounter.appointment and self.encounter.appointment.end:
                self.encounter.date_end = self.encounter.appointment.end
            else:
                self.encounter.date_end = timezone.now()
            
            # Устанавливаем исход и отделение
            self.encounter.outcome = self.get_outcome_code()
            self.encounter.transfer_to_department = transfer_department
            self.encounter.save()
            
            # Публикуем событие
            event = EncounterClosedEvent(
                encounter=self.encounter,
                outcome=self.get_outcome_code(),
                transfer_department=transfer_department,
                user=kwargs.get('user')
            )
            event_bus.publish(event)
            
            return True
    
    def get_required_fields(self) -> list:
        return ['documents', 'transfer_department']


class OutcomeStrategyFactory:
    """Фабрика для создания стратегий исходов"""
    
    _strategies = {
        'consultation_end': ConsultationEndStrategy,
        'transferred': TransferStrategy,
    }
    
    @classmethod
    def create_strategy(cls, outcome_code: str, encounter: Encounter) -> Optional[OutcomeStrategy]:
        """Создает стратегию по коду исхода"""
        strategy_class = cls._strategies.get(outcome_code)
        if strategy_class:
            return strategy_class(encounter)
        return None
    
    @classmethod
    def get_available_outcomes(cls) -> Dict[str, str]:
        """Возвращает доступные исходы с их отображаемыми названиями"""
        outcomes = {}
        for code, strategy_class in cls._strategies.items():
            # Создаем временный экземпляр для получения display name
            temp_encounter = Encounter()
            strategy = strategy_class(temp_encounter)
            outcomes[code] = strategy.get_outcome_display()
        return outcomes
    
    @classmethod
    def register_strategy(cls, outcome_code: str, strategy_class: type):
        """Регистрирует новую стратегию"""
        cls._strategies[outcome_code] = strategy_class


class OutcomeProcessor:
    """Процессор для обработки исходов encounters"""
    
    def __init__(self, encounter: Encounter):
        self.encounter = encounter
    
    def process_outcome(self, outcome_code: str, **kwargs) -> bool:
        """Обрабатывает исход encounter"""
        strategy = OutcomeStrategyFactory.create_strategy(outcome_code, self.encounter)
        
        if not strategy:
            raise ValueError(f"Unknown outcome code: {outcome_code}")
        
        return strategy.execute(**kwargs)
    
    def validate_outcome(self, outcome_code: str, **kwargs) -> bool:
        """Валидирует исход encounter"""
        strategy = OutcomeStrategyFactory.create_strategy(outcome_code, self.encounter)
        
        if not strategy:
            return False
        
        return strategy.validate(**kwargs)
    
    def get_outcome_requirements(self, outcome_code: str) -> Dict[str, list]:
        """Возвращает требования для исхода"""
        strategy = OutcomeStrategyFactory.create_strategy(outcome_code, self.encounter)
        
        if not strategy:
            return {}
        
        return {
            'required_fields': strategy.get_required_fields(),
            'optional_fields': strategy.get_optional_fields(),
            'display_name': strategy.get_outcome_display()
        } 