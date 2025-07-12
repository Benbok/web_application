from django.utils import timezone
from typing import Optional, Dict, Any

from ..models import Encounter
from patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()


class EncounterFactory:
    """
    Фабрика для создания случаев обращения.
    Инкапсулирует логику создания объектов с различными конфигурациями.
    """
    
    @staticmethod
    def create_encounter(
        patient: Patient,
        doctor: User,
        date_start: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание базового случая обращения.
        
        Args:
            patient: Пациент
            doctor: Врач
            date_start: Дата начала (по умолчанию текущее время)
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный Encounter
        """
        if date_start is None:
            date_start = timezone.now()
        
        return Encounter.objects.create(
            patient=patient,
            doctor=doctor,
            date_start=date_start,
            **kwargs
        )
    
    @staticmethod
    def create_encounter_with_appointment(
        patient: Patient,
        doctor: User,
        appointment,
        date_start: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание случая обращения с привязкой к записи на прием.
        
        Args:
            patient: Пациент
            doctor: Врач
            appointment: Запись на прием
            date_start: Дата начала
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный Encounter с привязкой к записи
        """
        encounter = EncounterFactory.create_encounter(
            patient=patient,
            doctor=doctor,
            date_start=date_start,
            **kwargs
        )
        
        # Привязываем к записи на прием
        appointment.encounter = encounter
        appointment.save(update_fields=['encounter'])
        
        return encounter
    
    @staticmethod
    def create_encounter_with_documents(
        patient: Patient,
        doctor: User,
        documents: list,
        date_start: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание случая обращения с документами.
        
        Args:
            patient: Пациент
            doctor: Врач
            documents: Список документов для создания
            date_start: Дата начала
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный Encounter с документами
        """
        encounter = EncounterFactory.create_encounter(
            patient=patient,
            doctor=doctor,
            date_start=date_start,
            **kwargs
        )
        
        # Создаем документы
        for document_data in documents:
            from documents.models import ClinicalDocument
            ClinicalDocument.objects.create(
                content_type=encounter.get_content_type(),
                object_id=encounter.id,
                **document_data
            )
        
        return encounter
    
    @staticmethod
    def create_closed_encounter(
        patient: Patient,
        doctor: User,
        outcome: str,
        transfer_department=None,
        date_start: Optional[timezone.datetime] = None,
        date_end: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание закрытого случая обращения.
        
        Args:
            patient: Пациент
            doctor: Врач
            outcome: Исход обращения
            transfer_department: Отделение для перевода
            date_start: Дата начала
            date_end: Дата завершения
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный закрытый Encounter
        """
        if date_start is None:
            date_start = timezone.now()
        
        if date_end is None:
            date_end = timezone.now()
        
        return Encounter.objects.create(
            patient=patient,
            doctor=doctor,
            date_start=date_start,
            date_end=date_end,
            outcome=outcome,
            transfer_to_department=transfer_department,
            is_active=False,
            **kwargs
        )
    
    @staticmethod
    def create_transfer_encounter(
        patient: Patient,
        doctor: User,
        transfer_department,
        date_start: Optional[timezone.datetime] = None,
        date_end: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание случая обращения с переводом в отделение.
        
        Args:
            patient: Пациент
            doctor: Врач
            transfer_department: Отделение для перевода
            date_start: Дата начала
            date_end: Дата завершения
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный Encounter с переводом
        """
        return EncounterFactory.create_closed_encounter(
            patient=patient,
            doctor=doctor,
            outcome='transferred',
            transfer_department=transfer_department,
            date_start=date_start,
            date_end=date_end,
            **kwargs
        )
    
    @staticmethod
    def create_consultation_encounter(
        patient: Patient,
        doctor: User,
        date_start: Optional[timezone.datetime] = None,
        date_end: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание случая обращения с завершением консультации.
        
        Args:
            patient: Пациент
            doctor: Врач
            date_start: Дата начала
            date_end: Дата завершения
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный Encounter с завершением консультации
        """
        return EncounterFactory.create_closed_encounter(
            patient=patient,
            doctor=doctor,
            outcome='consultation_end',
            date_start=date_start,
            date_end=date_end,
            **kwargs
        )
    
    @staticmethod
    def create_archived_encounter(
        patient: Patient,
        doctor: User,
        archived_at: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Encounter:
        """
        Создание архивированного случая обращения.
        
        Args:
            patient: Пациент
            doctor: Врач
            archived_at: Дата архивирования
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданный архивированный Encounter
        """
        if archived_at is None:
            archived_at = timezone.now()
        
        encounter = EncounterFactory.create_encounter(
            patient=patient,
            doctor=doctor,
            **kwargs
        )
        
        # Архивируем
        encounter.is_archived = True
        encounter.archived_at = archived_at
        encounter.save(update_fields=['is_archived', 'archived_at'])
        
        return encounter
    
    @staticmethod
    def create_encounter_from_dict(data: Dict[str, Any]) -> Encounter:
        """
        Создание случая обращения из словаря данных.
        
        Args:
            data: Словарь с данными для создания
            
        Returns:
            Созданный Encounter
        """
        # Извлекаем обязательные поля
        patient = data.pop('patient')
        doctor = data.pop('doctor')
        
        # Обрабатываем даты
        date_start = data.pop('date_start', None)
        if date_start and isinstance(date_start, str):
            from django.utils.dateparse import parse_datetime
            date_start = parse_datetime(date_start)
        
        date_end = data.pop('date_end', None)
        if date_end and isinstance(date_end, str):
            from django.utils.dateparse import parse_datetime
            date_end = parse_datetime(date_end)
        
        # Создаем случай обращения
        encounter = Encounter.objects.create(
            patient=patient,
            doctor=doctor,
            date_start=date_start or timezone.now(),
            date_end=date_end,
            **data
        )
        
        return encounter
    
    @staticmethod
    def create_encounter_batch(
        patients: list,
        doctor: User,
        **kwargs
    ) -> list:
        """
        Создание нескольких случаев обращения для списка пациентов.
        
        Args:
            patients: Список пациентов
            doctor: Врач
            **kwargs: Дополнительные параметры
            
        Returns:
            Список созданных Encounter
        """
        encounters = []
        for patient in patients:
            encounter = EncounterFactory.create_encounter(
                patient=patient,
                doctor=doctor,
                **kwargs
            )
            encounters.append(encounter)
        
        return encounters
    
    @staticmethod
    def create_test_encounter(**kwargs) -> Encounter:
        """
        Создание тестового случая обращения.
        
        Args:
            **kwargs: Дополнительные параметры
            
        Returns:
            Тестовый Encounter
        """
        from patients.models import Patient
        
        # Создаем тестового пациента если не передан
        if 'patient' not in kwargs:
            patient, created = Patient.objects.get_or_create(
                first_name='Тест',
                last_name='Пациент',
                defaults={
                    'middle_name': 'Тестович',
                    'birth_date': '1990-01-01',
                }
            )
            kwargs['patient'] = patient
        
        # Создаем тестового врача если не передан
        if 'doctor' not in kwargs:
            doctor, created = User.objects.get_or_create(
                username='test_doctor',
                defaults={
                    'first_name': 'Тест',
                    'last_name': 'Врач',
                    'email': 'test@example.com',
                }
            )
            kwargs['doctor'] = doctor
        
        return EncounterFactory.create_encounter(**kwargs) 