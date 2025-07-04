# pharmacy/models.py
from django.db import models


class Medication(models.Model):
    """
    Модель-справочник. Хранит только основную информацию о препарате.
    """
    name = models.CharField("Название препарата (МНН)", max_length=255, unique=True,
                            help_text="Международное непатентованное наименование")
    form = models.CharField("Форма выпуска", max_length=100, blank=True, null=True,
                            help_text="Например, 'таблетки', 'раствор для инъекций'")
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Препарат"
        verbose_name_plural = "Препараты"
        ordering = ['name']

    def __str__(self):
        return self.name


class DosingRule(models.Model):
    """
    Модель для хранения одного правила дозирования для конкретного препарата.
    У одного препарата может быть много правил.
    """
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='dosing_rules',
                                   verbose_name="Препарат")

    # --- Критерии применения этого правила ---
    name = models.CharField("Название правила", max_length=255,
                            help_text="Краткое описание для кого это правило, н-р: 'Дети до 12 лет <40кг'")

    ROUTE_CHOICES = [
        ('oral', 'Внутрь'),
        ('iv', 'Внутривенно'),
        ('im', 'Внутримышечно'),
        ('subcutaneous', 'Подкожно'),
        ('other', 'Другое'),
    ]
    route_of_administration = models.CharField("Путь введения", max_length=20, choices=ROUTE_CHOICES, blank=True,
                                               null=True)

    min_age_days = models.PositiveIntegerField("Минимальный возраст (дней)", blank=True, null=True)
    max_age_days = models.PositiveIntegerField("Максимальный возраст (дней)", blank=True, null=True)

    min_weight_kg = models.DecimalField("Минимальный вес (кг)", max_digits=5, decimal_places=2, blank=True, null=True)
    max_weight_kg = models.DecimalField("Максимальный вес (кг)", max_digits=5, decimal_places=2, blank=True, null=True)

    # --- Параметры самого дозирования ---
    is_loading_dose = models.BooleanField("Это начальная (нагрузочная) доза?", default=False)

    dosage_value = models.DecimalField("Значение дозы", max_digits=10, decimal_places=3, blank=True, null=True,
                                       help_text="Например, 10 или 500")
    dosage_unit = models.CharField("Единица дозы", max_length=50, blank=True, null=True,
                                   help_text="Например, 'мг/кг/сутки' или 'мг'")

    frequency_text = models.CharField("Текст частоты", max_length=100, blank=True, null=True,
                                      help_text="Например, 'каждые 12-24 часа' или '2-3 раза в сутки'")

    max_daily_dosage_text = models.CharField("Максимальная суточная доза (текст)", max_length=100, blank=True,
                                             null=True, help_text="Например, 'не более 4 г/сутки'")

    notes = models.TextField("Примечания", blank=True, null=True,
                             help_text="Например, '3-дневный курс', 'вводить в течение 1-2 часов'")

    class Meta:
        verbose_name = "Правило дозирования"
        verbose_name_plural = "Правила дозирования"
        ordering = ['medication', 'min_age_days']

    def __str__(self):
        return f"{self.medication.name} - {self.name}"