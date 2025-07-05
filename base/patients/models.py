from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from datetime import date

class Patient(models.Model):
    PATIENT_TYPE_CHOICES = [
        ('adult', 'Взрослый'),
        ('newborn', 'Новорожденный'),
        ('child', 'Ребенок'),
        ('teen', 'Подросток')
    ]
    patient_type = models.CharField(
        "Тип пациента",
        max_length=10,
        choices=PATIENT_TYPE_CHOICES,
        default='adult',
    )
    parents = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='children',
        verbose_name="Родители"
    )

    # FHIR: name
    last_name = models.CharField("Фамилия", max_length=100)
    first_name = models.CharField("Имя", max_length=100)
    middle_name = models.CharField("Отчество", max_length=100, blank=True, null=True)

    # FHIR: birthDate
    birth_date = models.DateField("Дата рождения")

    # FHIR: gender
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
        ('other', 'Другой'),
        ('unknown', 'Неизвестно'),
    ]
    gender = models.CharField("Пол", max_length=10, choices=GENDER_CHOICES)

    # FHIR: telecom
    phone = models.CharField("Телефон", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)

    # FHIR: address
    registration_address = models.TextField("Адрес регистрации", blank=True)
    residential_address = models.TextField("Адрес проживания", blank=True)

    # FHIR: identifier
    snils = models.CharField("СНИЛС", max_length=14, blank=True)
    insurance_policy_number = models.CharField("Полис ОМС/ДМС", max_length=30, blank=True)
    insurance_company = models.CharField("Страховая компания", max_length=100, blank=True)

    passport_series = models.CharField("Серия паспорта", max_length=4, blank=True)
    passport_number = models.CharField("Номер паспорта", max_length=6, blank=True)
    passport_issued_by = models.CharField("Кем выдан", max_length=255, blank=True)
    passport_issued_date = models.DateField("Дата выдачи", blank=True, null=True)
    passport_department_code = models.CharField(
        "Код подразделения", max_length=7, blank=True)

    # FHIR: contact (представитель пациента)
    legal_representative_full_name = models.CharField("ФИО представителя", max_length=200, blank=True)
    legal_representative_relation = models.CharField("Родство / статус", max_length=100, blank=True)
    legal_representative_contacts = models.CharField("Контакты представителя", max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Пациент"
        verbose_name_plural = "Пациенты"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()

    @property
    def age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

    @property
    def newborn_profile(self):
        if self.patient_type == 'newborn':
            return getattr(self, '_newborn_profile', None)
        return None
