from django.db import models
from patients.models import Patient

class NewbornProfile(models.Model):
    # Связь "один-к-одному" с основной моделью пациента
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='_newborn_profile', # Используем "приватное" имя
        verbose_name="Пациент"
    )

    

    # Специфические поля для новорожденных
    birth_datetime = models.DateTimeField("Дата и время рождения", null=True)
    gestational_age_weeks = models.PositiveIntegerField("Срок гестации (недель)")
    birth_weight_grams = models.PositiveIntegerField("Вес при рождении (грамм)")
    birth_height_cm = models.PositiveIntegerField("Рост при рождении (см)")
    head_circumference_cm = models.DecimalField("Окружность головы (см)", max_digits=4, decimal_places=1)
    apgar_score_1_min = models.PositiveIntegerField("Оценка по Апгар на 1-й минуте")
    apgar_score_5_min = models.PositiveIntegerField("Оценка по Апгар на 5-й минуте")

    notes = models.TextField("Особенности течения родов и раннего периода", blank=True)

    class Meta:
        verbose_name = "Профиль новорожденного"
        verbose_name_plural = "Профили новорожденных"

    def __str__(self):
        return f"Профиль новорожденного для {self.patient.full_name}"
