# pharmacy/services.py
from datetime import date
from collections import defaultdict
from django.db.models import Q
from .models import DosingRule

def get_medication_recommendations(patient, diagnosis=None, allergies_med_ids=None):
    """
    Подбирает подходящие правила дозирования для пациента на основе фильтров.

    :param patient: Объект пациента, должен иметь атрибуты birth_date и weight_kg.
    :param diagnosis: Объект Diagnosis (опционально).
    :param allergies_med_ids: Список ID препаратов, на которые у пациента аллергия (опционально).
    :return: Словарь, сгруппированный по названию группы препаратов.
    """
    if not patient or not patient.birth_date:
        return {}

    # 1. Рассчитываем данные пациента
    age_in_days = (date.today() - patient.birth_date).days
    weight_kg = patient.weight_kg

    # 2. Начинаем строить запрос. Сразу оптимизируем его, чтобы избежать лишних запросов к БД.
    rules_qs = DosingRule.objects.select_related(
        'medication', 'medication__group'
    ).prefetch_related('indications').all()

    # 3. Фильтруем по диагнозу, если он указан
    if diagnosis:
        rules_qs = rules_qs.filter(indications=diagnosis)

    # 4. Исключаем препараты, на которые есть аллергия
    if allergies_med_ids:
        rules_qs = rules_qs.exclude(medication_id__in=allergies_med_ids)

    # 5. Фильтруем по возрасту. Логика обрабатывает случаи, когда min или max возраст не указан (null).
    age_filter = (Q(min_age_days__lte=age_in_days) | Q(min_age_days__isnull=True)) & \
                 (Q(max_age_days__gte=age_in_days) | Q(max_age_days__isnull=True))
    rules_qs = rules_qs.filter(age_filter)

    # 6. Фильтруем по весу, если он известен. Аналогичная логика с null.
    if weight_kg:
        weight_filter = (Q(min_weight_kg__lte=weight_kg) | Q(min_weight_kg__isnull=True)) & \
                        (Q(max_weight_kg__gte=weight_kg) | Q(max_weight_kg__isnull=True))
        rules_qs = rules_qs.filter(weight_filter)

    # 7. Формируем итоговый структурированный ответ
    grouped_recommendations = defaultdict(list)

    for rule in rules_qs:
        group_name = rule.medication.group.name if rule.medication.group else "Без группы"
        
        # Здесь можно добавить логику расчета конкретной дозы, если требуется
        # Например: calculated_dose = rule.dosage_value * weight_kg
        
        recommendation = {
            'medication_id': rule.medication.id,
            'medication_name': rule.medication.name,
            'medication_form': rule.medication.form,
            'rule_name': rule.name,
            'dosage_value': rule.dosage_value,
            'dosage_unit': rule.dosage_unit,
            'frequency': rule.frequency_text,
            'notes': rule.notes,
        }
        grouped_recommendations[group_name].append(recommendation)

    return dict(grouped_recommendations)