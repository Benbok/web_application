from abc import ABC, abstractmethod
from typing import Dict, List, Set, Any, Callable
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

from ..models import Encounter
from ..events.encounter_events import EncounterEvent

User = get_user_model()


class Observer(ABC):
    """Базовый класс для всех наблюдателей"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.observations_count = 0
    
    @abstractmethod
    def update(self, event: EncounterEvent) -> None:
        """Обновляется при получении события"""
        pass
    
    def get_name(self) -> str:
        """Возвращает имя наблюдателя"""
        return self.name
    
    def get_observations_count(self) -> int:
        """Возвращает количество наблюдений"""
        return self.observations_count


class Subject(ABC):
    """Базовый класс для субъектов, за которыми наблюдают"""
    
    def __init__(self):
        self._observers: Set[Observer] = set()
    
    def attach(self, observer: Observer) -> None:
        """Прикрепляет наблюдателя"""
        self._observers.add(observer)
    
    def detach(self, observer: Observer) -> None:
        """Открепляет наблюдателя"""
        self._observers.discard(observer)
    
    def notify(self, event: EncounterEvent) -> None:
        """Уведомляет всех наблюдателей"""
        for observer in self._observers:
            try:
                observer.update(event)
                observer.observations_count += 1
            except Exception as e:
                print(f"Ошибка в наблюдателе {observer.get_name()}: {e}")


class LoggingObserver(Observer):
    """Наблюдатель для логирования событий"""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__("LoggingObserver")
        self.log_level = log_level
    
    def update(self, event: EncounterEvent) -> None:
        """Логирует событие"""
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        user_info = f" пользователем {event.user.username}" if event.user else ""
        
        log_message = f"[{timestamp}] {event.get_description()}{user_info}"
        
        if self.log_level == "DEBUG":
            log_message += f" (метаданные: {event.metadata})"
        
        print(f"[{self.log_level}] {log_message}")


class MetricsObserver(Observer):
    """Наблюдатель для сбора метрик"""
    
    def __init__(self):
        super().__init__("MetricsObserver")
        self.metrics = {
            'total_events': 0,
            'events_by_type': {},
            'events_by_user': {},
            'events_by_encounter': {},
            'last_event_time': None
        }
    
    def update(self, event: EncounterEvent) -> None:
        """Обновляет метрики"""
        event_type = event.get_event_type()
        user_id = event.user.id if event.user else 'anonymous'
        encounter_id = event.encounter.id
        
        # Общие метрики
        self.metrics['total_events'] += 1
        self.metrics['last_event_time'] = event.timestamp
        
        # Метрики по типам событий
        if event_type not in self.metrics['events_by_type']:
            self.metrics['events_by_type'][event_type] = 0
        self.metrics['events_by_type'][event_type] += 1
        
        # Метрики по пользователям
        if user_id not in self.metrics['events_by_user']:
            self.metrics['events_by_user'][user_id] = 0
        self.metrics['events_by_user'][user_id] += 1
        
        # Метрики по encounters
        if encounter_id not in self.metrics['events_by_encounter']:
            self.metrics['events_by_encounter'][encounter_id] = 0
        self.metrics['events_by_encounter'][encounter_id] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает текущие метрики"""
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Сбрасывает метрики"""
        self.metrics = {
            'total_events': 0,
            'events_by_type': {},
            'events_by_user': {},
            'events_by_encounter': {},
            'last_event_time': None
        }


class NotificationObserver(Observer):
    """Наблюдатель для отправки уведомлений"""
    
    def __init__(self, notification_channels: List[str] = None):
        super().__init__("NotificationObserver")
        self.notification_channels = notification_channels or ['email', 'sms']
        self.notification_history = []
    
    def update(self, event: EncounterEvent) -> None:
        """Отправляет уведомления"""
        event_type = event.get_event_type()
        
        # Определяем, какие уведомления отправлять
        notifications = self._determine_notifications(event_type, event)
        
        for notification in notifications:
            self._send_notification(notification)
            self.notification_history.append({
                'timestamp': event.timestamp,
                'event_type': event_type,
                'notification': notification
            })
    
    def _determine_notifications(self, event_type: str, event: EncounterEvent) -> List[Dict[str, Any]]:
        """Определяет, какие уведомления отправлять"""
        notifications = []
        
        if event_type == 'encounter_closed':
            notifications.append({
                'type': 'email',
                'recipient': event.encounter.patient.email if hasattr(event.encounter.patient, 'email') else None,
                'subject': 'Случай обращения закрыт',
                'message': f'Ваш случай обращения от {event.encounter.date_start.strftime("%d.%m.%Y")} был закрыт.'
            })
        
        elif event_type == 'encounter_reopened':
            notifications.append({
                'type': 'email',
                'recipient': event.encounter.patient.email if hasattr(event.encounter.patient, 'email') else None,
                'subject': 'Случай обращения возобновлен',
                'message': f'Ваш случай обращения от {event.encounter.date_start.strftime("%d.%m.%Y")} был возобновлен.'
            })
        
        return notifications
    
    def _send_notification(self, notification: Dict[str, Any]) -> None:
        """Отправляет уведомление (заглушка)"""
        print(f"Отправка уведомления: {notification}")
        # Здесь была бы реальная логика отправки уведомлений
    
    def get_notification_history(self) -> List[Dict[str, Any]]:
        """Возвращает историю уведомлений"""
        return self.notification_history.copy()


class AuditObserver(Observer):
    """Наблюдатель для аудита"""
    
    def __init__(self, audit_file: str = "encounter_audit.log"):
        super().__init__("AuditObserver")
        self.audit_file = audit_file
        self.audit_entries = []
    
    def update(self, event: EncounterEvent) -> None:
        """Записывает аудит"""
        audit_entry = {
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.get_event_type(),
            'encounter_id': event.encounter.id,
            'user_id': event.user.id if event.user else None,
            'user_username': event.user.username if event.user else None,
            'description': event.get_description(),
            'metadata': event.metadata
        }
        
        self.audit_entries.append(audit_entry)
        self._write_to_file(audit_entry)
    
    def _write_to_file(self, audit_entry: Dict[str, Any]) -> None:
        """Записывает в файл аудита"""
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(f"{audit_entry['timestamp']} | {audit_entry['event_type']} | "
                       f"Encounter {audit_entry['encounter_id']} | "
                       f"User {audit_entry['user_username']} | "
                       f"{audit_entry['description']}\n")
        except Exception as e:
            print(f"Ошибка записи в файл аудита: {e}")
    
    def get_audit_entries(self) -> List[Dict[str, Any]]:
        """Возвращает записи аудита"""
        return self.audit_entries.copy()


class PerformanceObserver(Observer):
    """Наблюдатель для мониторинга производительности"""
    
    def __init__(self):
        super().__init__("PerformanceObserver")
        self.performance_metrics = {
            'event_processing_times': [],
            'average_processing_time': 0,
            'slowest_events': []
        }
    
    def update(self, event: EncounterEvent) -> None:
        """Измеряет производительность обработки события"""
        start_time = timezone.now()
        
        # Симуляция обработки события
        import time
        time.sleep(0.001)  # Имитация обработки
        
        processing_time = (timezone.now() - start_time).total_seconds()
        
        # Сохраняем метрики
        self.performance_metrics['event_processing_times'].append(processing_time)
        
        # Обновляем среднее время
        times = self.performance_metrics['event_processing_times']
        self.performance_metrics['average_processing_time'] = sum(times) / len(times)
        
        # Отслеживаем медленные события
        if processing_time > 0.1:  # Более 100ms
            self.performance_metrics['slowest_events'].append({
                'event_type': event.get_event_type(),
                'processing_time': processing_time,
                'timestamp': event.timestamp
            })
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики производительности"""
        return self.performance_metrics.copy()


class ObserverManager:
    """Менеджер для управления наблюдателями"""
    
    def __init__(self):
        self.observers: Dict[str, Observer] = {}
        self.subject = Subject()
    
    def register_observer(self, name: str, observer: Observer) -> None:
        """Регистрирует наблюдателя"""
        if name not in self.observers:  # Проверяем, не зарегистрирован ли уже
            self.observers[name] = observer
            self.subject.attach(observer)
            print(f"Наблюдатель {name} зарегистрирован")
        # else:
        #     print(f"Наблюдатель {name} уже зарегистрирован")
    
    def unregister_observer(self, name: str) -> None:
        """Отменяет регистрацию наблюдателя"""
        if name in self.observers:
            observer = self.observers.pop(name)
            self.subject.detach(observer)
            print(f"Наблюдатель {name} отменен")
    
    def notify_observers(self, event: EncounterEvent) -> None:
        """Уведомляет всех наблюдателей"""
        self.subject.notify(event)
    
    def get_observer(self, name: str) -> Observer:
        """Возвращает наблюдателя по имени"""
        return self.observers.get(name)
    
    def get_all_observers(self) -> Dict[str, Observer]:
        """Возвращает всех наблюдателей"""
        return self.observers.copy()
    
    def get_observer_stats(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает статистику наблюдателей"""
        stats = {}
        for name, observer in self.observers.items():
            stats[name] = {
                'name': observer.get_name(),
                'observations_count': observer.get_observations_count(),
                'type': observer.__class__.__name__
            }
        return stats


# Глобальный менеджер наблюдателей
observer_manager = ObserverManager()

# Флаг для предотвращения повторной регистрации
_observers_registered = False

def register_default_observers():
    """Регистрирует стандартных наблюдателей только один раз"""
    global _observers_registered
    
    if _observers_registered:
        return
    
    # Регистрация стандартных наблюдателей
    observer_manager.register_observer('logging', LoggingObserver())
    observer_manager.register_observer('metrics', MetricsObserver())
    observer_manager.register_observer('notifications', NotificationObserver())
    observer_manager.register_observer('audit', AuditObserver())
    observer_manager.register_observer('performance', PerformanceObserver())
    
    _observers_registered = True

# Регистрируем наблюдателей при первом импорте
register_default_observers() 