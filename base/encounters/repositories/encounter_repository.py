from typing import List, Optional, Dict, Any
from django.db.models import QuerySet
from django.core.exceptions import ObjectDoesNotExist

from ..models import Encounter
from patients.models import Patient


class EncounterRepository:
    """
    Репозиторий для работы с данными случаев обращения.
    Абстрагирует доступ к базе данных и предоставляет удобные методы.
    """
    
    def get_by_id(self, encounter_id: int) -> Optional[Encounter]:
        """
        Получение случая обращения по ID.
        
        Args:
            encounter_id: ID случая обращения
            
        Returns:
            Encounter или None если не найден
        """
        try:
            return Encounter.objects.get(id=encounter_id)
        except ObjectDoesNotExist:
            return None
    
    def get_active_by_id(self, encounter_id: int) -> Optional[Encounter]:
        """
        Получение активного случая обращения по ID.
        
        Args:
            encounter_id: ID случая обращения
            
        Returns:
            Активный Encounter или None если не найден или не активен
        """
        try:
            return Encounter.objects.get(id=encounter_id, is_active=True)
        except ObjectDoesNotExist:
            return None
    
    def get_with_documents(self, encounter_id: int) -> Optional[Encounter]:
        """
        Получение случая обращения с предзагруженными документами.
        
        Args:
            encounter_id: ID случая обращения
            
        Returns:
            Encounter с документами или None если не найден
        """
        try:
            return Encounter.objects.prefetch_related('documents').get(id=encounter_id)
        except ObjectDoesNotExist:
            return None
    
    def get_with_related_data(self, encounter_id: int) -> Optional[Encounter]:
        """
        Получение случая обращения с предзагруженными связанными данными.
        
        Args:
            encounter_id: ID случая обращения
            
        Returns:
            Encounter с связанными данными или None если не найден
        """
        try:
            return Encounter.objects.select_related(
                'patient', 'doctor', 'transfer_to_department'
            ).prefetch_related('documents').get(id=encounter_id)
        except ObjectDoesNotExist:
            return None
    
    def get_by_patient(self, patient: Patient) -> QuerySet[Encounter]:
        """
        Получение всех случаев обращения пациента.
        
        Args:
            patient: Пациент
            
        Returns:
            QuerySet случаев обращения
        """
        return Encounter.objects.filter(patient=patient).select_related('doctor').order_by('-date_start')
    
    def get_active_by_patient(self, patient: Patient) -> QuerySet[Encounter]:
        """
        Получение активных случаев обращения пациента.
        
        Args:
            patient: Пациент
            
        Returns:
            QuerySet активных случаев обращения
        """
        return Encounter.objects.filter(
            patient=patient, 
            is_active=True
        ).select_related('doctor').order_by('-date_start')
    
    def get_by_doctor(self, doctor_id: int) -> QuerySet[Encounter]:
        """
        Получение случаев обращения по врачу.
        
        Args:
            doctor_id: ID врача
            
        Returns:
            QuerySet случаев обращения
        """
        return Encounter.objects.filter(
            doctor_id=doctor_id
        ).select_related('patient').order_by('-date_start')
    
    def get_active_by_doctor(self, doctor_id: int) -> QuerySet[Encounter]:
        """
        Получение активных случаев обращения по врачу.
        
        Args:
            doctor_id: ID врача
            
        Returns:
            QuerySet активных случаев обращения
        """
        return Encounter.objects.filter(
            doctor_id=doctor_id,
            is_active=True
        ).select_related('patient').order_by('-date_start')
    
    def get_by_department(self, department_id: int) -> QuerySet[Encounter]:
        """
        Получение случаев обращения, переведенных в отделение.
        
        Args:
            department_id: ID отделения
            
        Returns:
            QuerySet случаев обращения
        """
        return Encounter.objects.filter(
            transfer_to_department_id=department_id
        ).select_related('patient', 'doctor').order_by('-date_start')
    
    def get_encounter_number(self, encounter: Encounter) -> int:
        """
        Вычисление номера обращения для пациента.
        
        Args:
            encounter: Случай обращения
            
        Returns:
            Номер обращения (начиная с 1)
        """
        return Encounter.objects.filter(
            patient_id=encounter.patient_id,
            date_start__lt=encounter.date_start
        ).count() + 1
    
    def get_patient_encounters_count(self, patient: Patient) -> int:
        """
        Получение количества случаев обращения пациента.
        
        Args:
            patient: Пациент
            
        Returns:
            Количество случаев обращения
        """
        return Encounter.objects.filter(patient=patient).count()
    
    def get_active_encounters_count(self) -> int:
        """
        Получение количества активных случаев обращения.
        
        Returns:
            Количество активных случаев обращения
        """
        return Encounter.objects.filter(is_active=True).count()
    
    def get_encounters_by_date_range(self, start_date, end_date) -> QuerySet[Encounter]:
        """
        Получение случаев обращения за период.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            QuerySet случаев обращения за период
        """
        return Encounter.objects.filter(
            date_start__gte=start_date,
            date_start__lte=end_date
        ).select_related('patient', 'doctor').order_by('-date_start')
    
    def get_encounters_by_outcome(self, outcome: str) -> QuerySet[Encounter]:
        """
        Получение случаев обращения по исходу.
        
        Args:
            outcome: Исход обращения
            
        Returns:
            QuerySet случаев обращения с указанным исходом
        """
        return Encounter.objects.filter(
            outcome=outcome
        ).select_related('patient', 'doctor').order_by('-date_start')
    
    def get_encounters_without_documents(self) -> QuerySet[Encounter]:
        """
        Получение случаев обращения без документов.
        
        Returns:
            QuerySet случаев обращения без документов
        """
        return Encounter.objects.filter(
            documents__isnull=True
        ).select_related('patient', 'doctor').order_by('-date_start')
    
    def get_encounters_with_documents(self) -> QuerySet[Encounter]:
        """
        Получение случаев обращения с документами.
        
        Returns:
            QuerySet случаев обращения с документами
        """
        return Encounter.objects.filter(
            documents__isnull=False
        ).select_related('patient', 'doctor').prefetch_related('documents').order_by('-date_start')
    
    def get_recent_encounters(self, limit: int = 10) -> QuerySet[Encounter]:
        """
        Получение последних случаев обращения.
        
        Args:
            limit: Количество случаев
            
        Returns:
            QuerySet последних случаев обращения
        """
        return Encounter.objects.select_related(
            'patient', 'doctor'
        ).order_by('-date_start')[:limit]
    
    def get_encounters_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по случаям обращения.
        
        Returns:
            Dict со статистикой
        """
        total_encounters = Encounter.objects.count()
        active_encounters = Encounter.objects.filter(is_active=True).count()
        closed_encounters = Encounter.objects.filter(is_active=False).count()
        
        consultation_end_count = Encounter.objects.filter(outcome='consultation_end').count()
        transferred_count = Encounter.objects.filter(outcome='transferred').count()
        
        return {
            'total': total_encounters,
            'active': active_encounters,
            'closed': closed_encounters,
            'consultation_end': consultation_end_count,
            'transferred': transferred_count,
        }
    
    def create_encounter(self, **kwargs) -> Encounter:
        """
        Создание нового случая обращения.
        
        Args:
            **kwargs: Параметры для создания случая
            
        Returns:
            Созданный Encounter
        """
        return Encounter.objects.create(**kwargs)
    
    def update_encounter(self, encounter: Encounter, **kwargs) -> Encounter:
        """
        Обновление случая обращения.
        
        Args:
            encounter: Случай обращения для обновления
            **kwargs: Параметры для обновления
            
        Returns:
            Обновленный Encounter
        """
        for key, value in kwargs.items():
            setattr(encounter, key, value)
        encounter.save()
        return encounter
    
    def delete_encounter(self, encounter: Encounter) -> None:
        """
        Удаление случая обращения.
        
        Args:
            encounter: Случай обращения для удаления
        """
        encounter.delete()
    
    def archive_encounter(self, encounter: Encounter) -> None:
        """
        Архивирование случая обращения.
        
        Args:
            encounter: Случай обращения для архивирования
        """
        encounter.archive()
    
    def unarchive_encounter(self, encounter: Encounter) -> None:
        """
        Восстановление случая обращения из архива.
        
        Args:
            encounter: Случай обращения для восстановления
        """
        encounter.unarchive() 