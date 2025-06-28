from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date

class Patient(models.Model):
    # FHIR: name
    family = models.CharField("Фамилия", max_length=100)
    given = models.CharField("Имя", max_length=100)
    middle = models.CharField("Отчество", max_length=100, blank=True, null=True)

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
    address_text = models.TextField("Адрес (строкой)", blank=True)
    postal_code = models.CharField("Почтовый индекс", max_length=12, blank=True)
    city = models.CharField("Город", max_length=50, blank=True)
    country = models.CharField("Страна", max_length=50, blank=True)

    # FHIR: identifier
    snils = models.CharField("СНИЛС", max_length=14, blank=True)
    insurance_policy = models.CharField("Полис ОМС", max_length=30, blank=True)
    passport_number = models.CharField("Номер паспорта", max_length=20, blank=True)

    # Родственные связи
    parents = models.ManyToManyField('self', symmetrical=False, related_name='children', blank=True, verbose_name="Родители")
    guardian_name = models.CharField("ФИО законного представителя", max_length=200, blank=True)
    guardian_contact = models.CharField("Контакт представителя", max_length=50, blank=True)

    # FHIR: deceasedBoolean
    deceased = models.BooleanField("Умер", default=False)

    # Медицинская информация
    BLOOD_TYPE_CHOICES = [
        ('', '---------'),
        ('O(I)', 'O (I)'),
        ('A(II)', 'A (II)'),
        ('B(III)', 'B (III)'),
        ('AB(IV)', 'AB (IV)'),
    ]
    RHESUS_FACTOR_CHOICES = [
        ('', '---------'),
        ('+', 'Положительный (+)'),
        ('-', 'Отрицательный (-)'),
    ]
    blood_type = models.CharField("Группа крови", max_length=6, choices=BLOOD_TYPE_CHOICES, blank=True)
    rhesus_factor = models.CharField("Резус-фактор", max_length=1, choices=RHESUS_FACTOR_CHOICES, blank=True)
    allergies = models.TextField("Аллергии", blank=True)
    chronic_conditions = models.TextField("Хронические заболевания", blank=True)

    # Информация о новорожденных
    birth_weight = models.DecimalField("Вес при рождении (кг)", max_digits=4, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0.5)])
    birth_height = models.PositiveIntegerField("Рост при рождении (см)", blank=True, null=True)
    gestation_weeks = models.PositiveIntegerField("Срок гестации (нед.)", blank=True, null=True)

    # Метаданные
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Пациент"
        verbose_name_plural = "Пациенты"
        ordering = ['family', 'given']

    def __str__(self):
        return f"{self.family} {self.given} {self.middle or ''}".strip()

    @property
    def full_name(self):
        return f"{self.family} {self.given} {self.middle or ''}".strip()

    @property
    def age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None
    
    def clean(self):
        if self.parents.exists():
            for parent in self.parents.all():
                if parent.age is not None and parent.age < 16:
                    raise ValidationError(f"Родитель {parent.full_name} младше 16 лет и не может быть назначен родителем.")
