from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models import Q
from typing import Optional
import datetime
from base.models import ArchivableModel
from base.services import ArchiveManager


class Patient(ArchivableModel):
    class PatientType(models.TextChoices):
        ADULT = 'adult', 'Взрослый'
        NEWBORN = 'newborn', 'Новорожденный'
        CHILD = 'child', 'Ребенок'
        TEEN = 'teen', 'Подросток'

    class Gender(models.TextChoices):
        MALE = 'male', 'Мужской'
        FEMALE = 'female', 'Женский'
        OTHER = 'other', 'Другой'
        UNKNOWN = 'unknown', 'Неизвестно'

    patient_type: str = models.CharField(
        "Тип пациента",
        max_length=10,
        choices=PatientType.choices,
        default=PatientType.ADULT,
    )
    parents = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='children',
        verbose_name="Родители"
    )

    last_name: str = models.CharField("Фамилия", max_length=100)
    first_name: str = models.CharField("Имя", max_length=100)
    middle_name: Optional[str] = models.CharField("Отчество", max_length=100, blank=True, null=True)
    birth_date = models.DateField("Дата рождения")
    gender: str = models.CharField("Пол", max_length=10, choices=Gender.choices)

    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Пациент"
        verbose_name_plural = "Пациенты"
        ordering = ["last_name", "first_name", "birth_date"]
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['birth_date']),
            models.Index(fields=['is_archived']),
        ]

    def clean(self):
        if self.birth_date and self.birth_date > datetime.date.today():
            raise ValidationError("Дата рождения не может быть в будущем")

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name or '']
        return " ".join(part for part in parts if part)

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()
    
    def get_age(self):
        """
        Возвращает возраст пациента в годах
        """
        if not self.birth_date:
            return None
        
        today = datetime.date.today()
        age = today.year - self.birth_date.year
        
        # Проверяем, прошел ли день рождения в этом году
        if today.month < self.birth_date.month or (today.month == self.birth_date.month and today.day < self.birth_date.day):
            age -= 1
        
        return age
    
    def get_full_name_with_age(self):
        """
        Возвращает ФИО пациента с возрастом в скобках
        """
        age = self.get_age()
        if age is not None:
            return f"{self.full_name} ({age} лет)"
        return self.full_name
    
    def get_back_url(self):
        """Возвращает URL для возврата к детальному просмотру пациента"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.pk})
    
    # Менеджер для архивирования
    objects = ArchiveManager()
    
    def _archive_related_records(self, user, reason):
        """
        Архивирует связанные записи пациента
        """
        print(f"Начинаем архивирование связанных записей для пациента {self.pk}")
        
        # Архивируем контакты пациента
        try:
            # Проверяем, существует ли контакт пациента
            print(f"Проверяем контакт для пациента {self.pk}")
            
            # Используем правильную проверку для OneToOneField
            from django.core.exceptions import ObjectDoesNotExist
            try:
                contact = self.contact
                if contact and not contact.is_archived:
                    print(f"Архивируем контакт {contact.pk}")
                    contact.archive(user, f"Каскадное архивирование пациента: {reason}")
                    print(f"Контакт {contact.pk} успешно архивирован")
                elif contact and contact.is_archived:
                    print(f"Контакт {contact.pk} уже архивирован")
                else:
                    print("Контакт не существует (None)")
            except ObjectDoesNotExist:
                print("У пациента нет связанного контакта")
                
        except Exception as e:
            # Если контакт не существует или есть другие проблемы, пропускаем
            print(f"Ошибка при архивировании контакта пациента {self.pk}: {e}")
            import traceback
            traceback.print_exc()
            pass
        
        # Архивируем встречи пациента
        from encounters.models import Encounter
        encounters = Encounter.objects.filter(patient=self, is_archived=False)
        for encounter in encounters:
            encounter.archive(user, f"Каскадное архивирование пациента: {reason}")
        
        # Архивируем документы пациента
        from documents.models import ClinicalDocument
        documents = ClinicalDocument.objects.filter(
            Q(encounter__patient=self) | Q(patient_department_status__patient=self),
            is_archived=False
        )
        for document in documents:
            document.archive(user, f"Каскадное архивирование пациента: {reason}")
        
        # Архивируем назначения пациента
        from appointments.models import AppointmentEvent
        appointments = AppointmentEvent.objects.filter(patient=self, is_archived=False)
        for appointment in appointments:
            appointment.archive(user, f"Каскадное архивирование пациента: {reason}")
    
    def _restore_related_records(self, user):
        """
        Восстанавливает связанные записи пациента
        """
        # Восстанавливаем контакты пациента
        try:
            # Проверяем, существует ли контакт пациента
            from django.core.exceptions import ObjectDoesNotExist
            try:
                contact = self.contact
                if contact and contact.is_archived:
                    contact.restore(user)
                    print(f"Контакт {contact.pk} успешно восстановлен")
            except ObjectDoesNotExist:
                print("У пациента нет связанного контакта для восстановления")
        except Exception as e:
            # Если контакт не существует или есть другие проблемы, пропускаем
            print(f"Ошибка при восстановлении контакта пациента {self.pk}: {e}")
            pass
        
        # Восстанавливаем встречи пациента
        from encounters.models import Encounter
        encounters = Encounter.objects.filter(patient=self, is_archived=True)
        for encounter in encounters:
            encounter.restore(user)
        
        # Восстанавливаем документы пациента
        from documents.models import ClinicalDocument
        documents = ClinicalDocument.objects.filter(
            Q(encounter__patient=self) | Q(patient_department_status__patient=self),
            is_archived=True
        )
        for document in documents:
            document.restore(user)
        
        # Восстанавливаем назначения пациента
        from appointments.models import AppointmentEvent
        appointments = AppointmentEvent.objects.filter(patient=self, is_archived=True)
        for appointment in appointments:
            appointment.restore(user)


# FHIR: contact (представитель пациента)
class PatientContact(ArchivableModel):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='contact')
    phone = models.CharField("Телефон", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)
    legal_representative_full_name = models.CharField("ФИО представителя", max_length=200, blank=True)
    legal_representative_relation = models.CharField("Родство / статус", max_length=100, blank=True)
    legal_representative_contacts = models.CharField("Контакты представителя", max_length=100, blank=True)

    # Менеджеры для архивирования
    objects = ArchiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Контакт пациента"
        verbose_name_plural = "Контакты пациентов"


class PatientAddress(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='address')
    registration_address = models.TextField("Адрес регистрации", blank=True)
    residential_address = models.TextField("Адрес проживания", blank=True)

    class Meta:
        verbose_name = "Адрес пациента"
        verbose_name_plural = "Адреса пациентов"

 # FHIR: identifier
class PatientDocument(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='document')
    document_type = models.CharField("Тип документа", max_length=50, blank=True)
    passport_series = models.CharField("Серия паспорта", max_length=4, blank=True)
    passport_number = models.CharField("Номер паспорта", max_length=6, blank=True)
    passport_issued_by = models.CharField("Кем выдан", max_length=255, blank=True)
    passport_issued_date = models.DateField("Дата выдачи", blank=True, null=True)
    passport_department_code = models.CharField(
        "Код подразделения", max_length=7, blank=True)

    snils = models.CharField("СНИЛС", max_length=14, blank=True, null=True, unique=True)
    insurance_policy_number = models.CharField("Полис ОМС/ДМС", max_length=30, blank=True, null=True, unique=True)
    insurance_company = models.CharField("Страховая компания", max_length=100, blank=True)

    class Meta:
        verbose_name = "Документ пациента"
        verbose_name_plural = "Документы пациентов"

