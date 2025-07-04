from django.db import models

class Medication(models.Model):
    """
    Модель для хранения информации о препаратах.
    """
    name = models.CharField("Название препарата", max_length=255, unique=True)
    default_dosage = models.CharField("Дозировка по умолчанию", max_length=100, blank=True, null=True)
    default_frequency = models.CharField("Частота по умолчанию", max_length=100, blank=True, null=True)
    default_duration = models.CharField("Длительность по умолчанию", max_length=100, blank=True, null=True)
    unit = models.CharField("Единица измерения", max_length=50, blank=True, null=True)
    form = models.CharField("Форма выпуска", max_length=100, blank=True, null=True)
    description = models.TextField("Описание", blank=True, null=True)

    # Новые поля для педиатрических дозировок и гибкой частоты
    default_dosage_per_kg = models.DecimalField("Дозировка на кг по умолчанию", max_digits=10, decimal_places=3, blank=True, null=True)
    default_dosage_per_kg_unit = models.CharField("Единица дозировки на кг", max_length=50, blank=True, null=True)
    default_frequency_hours_options = models.CharField("Варианты частоты (часы)", max_length=255, blank=True, null=True, help_text="Через запятую, например: 12,24")
    default_route = models.CharField("Путь введения по умолчанию", max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Препарат"
        verbose_name_plural = "Препараты"
        ordering = ['name']

    def __str__(self):
        if self.default_dosage and self.unit:
            return f"{self.name} ({self.default_dosage} {self.unit})"
        return self.name
