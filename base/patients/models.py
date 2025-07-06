from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from typing import Optional
import datetime


class Patient(models.Model):
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

    def clean(self):
        if self.birth_date and self.birth_date > datetime.date.today():
            raise ValidationError("Дата рождения не может быть в будущем")

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name or '']
        return " ".join(part for part in parts if part)

# FHIR: contact (представитель пациента)
class PatientContact(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='contact')
    phone = models.CharField("Телефон", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)
    legal_representative_full_name = models.CharField("ФИО представителя", max_length=200, blank=True)
    legal_representative_relation = models.CharField("Родство / статус", max_length=100, blank=True)
    legal_representative_contacts = models.CharField("Контакты представителя", max_length=100, blank=True)

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

    snils = models.CharField("СНИЛС", max_length=14, blank=True, unique=True)
    insurance_policy_number = models.CharField("Полис ОМС/ДМС", max_length=30, blank=True, unique=True)
    insurance_company = models.CharField("Страховая компания", max_length=100, blank=True)

    class Meta:
        verbose_name = "Документ пациента"
        verbose_name_plural = "Документы пациентов"

