from django.db import models
from patients.models import Patient
from django.core.validators import MaxValueValidator, MinValueValidator
import os
from django.conf import settings
import json

weight_path = os.path.join(settings.BASE_DIR, 'base', 'newborns', 'static', 'newborns', 'weight_data.json')
length_path = os.path.join(settings.BASE_DIR, 'base', 'newborns', 'static', 'newborns', 'length_data.json')

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
    birth_time = models.TimeField("Время рождения", null=True)
    gestational_age_weeks = models.PositiveIntegerField("Срок гестации (недель)", help_text="Срок гестации, недель", 
                                                        validators=[MinValueValidator(22, message="Срок гестации должен быть не менее 22 недель"), 
                                                                    MaxValueValidator(44, message="Срок гестации должен быть не более 42 недель")])
    gestational_age_days = models.PositiveIntegerField("Срок гестации (дней)", help_text="Срок гестации, дней",
                                                        validators=[MinValueValidator(0, message="Срок гестации должен быть не менее 0 дней"), 
                                                                    MaxValueValidator(7, message="Срок гестации должен быть не более 7 дней")])
    
    birth_weight_grams = models.PositiveIntegerField("Вес при рождении (грамм)")
    birth_height_cm = models.PositiveIntegerField("Рост при рождении (см)")
    head_circumference_cm = models.DecimalField("Окружность головы (см)", max_digits=4, decimal_places=1)
    physical_development = models.TextField("Физическое развитие", blank=True)
    
    apgar_score_1_min = models.PositiveIntegerField("Оценка по Апгар на 1-й минуте", null=True)
    apgar_score_5_min = models.PositiveIntegerField("Оценка по Апгар на 5-й минуте", null=True)
    apgar_score_10_min = models.PositiveIntegerField("Оценка по Апгар на 10-й минуте", null=True)

    notes = models.TextField("Особенности течения беременности и родов", blank=True)
    obstetric_history = models.TextField("Акушерский диагноз", blank=True)

    def get_ga_key(self):
        return f"{self.gestational_age_weeks}+{self.gestational_age_days}"

    def load_centile_data(self):
        # Определяем пол: 'boys' или 'girls'
        gender = 'boys'
        patient = self.patient
        if patient and hasattr(patient, 'gender'):
            if patient.gender == 'female':
                gender = 'girls'
        weight_path = os.path.join(settings.BASE_DIR, 'newborns', 'static', 'newborns', gender, 'weight_data.json')
        length_path = os.path.join(settings.BASE_DIR, 'newborns', 'static', 'newborns', gender, 'length_data.json')
        with open(weight_path, encoding='utf-8') as f:
            weight_data = json.load(f)
        with open(length_path, encoding='utf-8') as f:
            length_data = json.load(f)
        return weight_data, length_data

    def calculate_physical_development(self):
        weight_data, length_data = self.load_centile_data()
        ga_key = self.get_ga_key()
        weight_kg = float(self.birth_weight_grams) / 1000.0  # конвертируем в кг
        length = self.birth_height_cm

        def get_centile_index(centiles, value):
            # Центили: [3rd, 10th, 25th, 50th, 75th, 90th, 97th]
            # Индексы: [0,    1,     2,     3,     4,     5,     6]
            for i, threshold in enumerate(centiles):
                if value <= threshold:
                    return i
            return len(centiles) - 1  # Если больше всех, возвращаем последний индекс

        def conclusion(weight_idx, length_idx):
            # Интерпретация индексов:
            # 0-1: Очень низкий вес (3rd-10th центиль)
            # 2: Низкий вес (25th центиль) 
            # 3: Нормальный вес (50th центиль)
            # 4: Высокий вес (75th центиль)
            # 5-6: Очень высокий вес (90th-97th центиль)
            
            if weight_idx <= 1:
                weight_note = "Маловесный для гестационного возраста"
            elif weight_idx == 2:
                weight_note = "Развитие гармоничное"
            elif weight_idx == 3:
                weight_note = "Развитие гармоничное"
            elif weight_idx == 4:
                weight_note = "Развитие гармоничное"
            elif weight_idx >= 5:
                weight_note = "Крупный новорожденный"
            else:
                weight_note = "Вес в пределах нормы"

            # Оценка гармоничности развития
            if 2 <= weight_idx <= 4 and 2 <= length_idx <= 4:
                harmony = "Гармоничное развитие"
            elif (weight_idx <= 1 or weight_idx >= 5) or (length_idx <= 1 or length_idx >= 5):
                harmony = "Дисгармоничное развитие"
            else:
                harmony = "Развитие в пределах нормы"
                
            return weight_note, harmony

        if ga_key in weight_data and ga_key in length_data:
            weight_centiles = weight_data[ga_key]
            length_centiles = length_data[ga_key]
            
            weight_idx = get_centile_index(weight_centiles, weight_kg)
            length_idx = get_centile_index(length_centiles, length)
            
            weight_result, harmony_result = conclusion(weight_idx, length_idx)
            
            # Добавляем детальную информацию для отладки
            debug_info = f" (вес: {weight_kg}кг, центили: {weight_centiles}, индекс: {weight_idx})"
            
            return f"Масса тела: {weight_result}. Гармоничность развития: {harmony_result}.{debug_info}"
        else:
            return "Нет данных для данного гестационного возраста."

    def save(self, *args, **kwargs):
        self.physical_development = self.calculate_physical_development()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Профиль новорожденного"
        verbose_name_plural = "Профили новорожденных"

    def __str__(self):
        patient = self.patient
        if patient and hasattr(patient, 'full_name'):
            return f"Профиль новорожденного для {patient.full_name}"
        return f"Профиль новорожденного для {str(patient)}"

