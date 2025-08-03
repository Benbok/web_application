# pharmacy/services.py
from datetime import date
from collections import defaultdict
from typing import List, Dict, Optional, Tuple
from django.db.models import Q, Prefetch
from django.core.exceptions import ValidationError

from .models import (
    Medication, TradeName, Regimen, PopulationCriteria, 
    DosingInstruction, RegimenAdjustment, MedicationGroup,
    ReleaseForm, AdministrationMethod
)
from patients.models import Patient
from diagnosis.models import Diagnosis


class MedicationService:
    """Сервис для работы с препаратами и торговыми наименованиями."""
    
    @staticmethod
    def get_medications_by_group(group_id: Optional[int] = None) -> List[Dict]:
        """
        Получает список препаратов, сгруппированных по фармакологическим группам.
        
        :param group_id: ID конкретной группы (опционально)
        :return: Список словарей с информацией о препаратах
        """
        queryset = TradeName.objects.select_related(
            'medication', 'medication_group', 'release_form'
        ).prefetch_related('medication__regimens')
        
        if group_id:
            queryset = queryset.filter(medication_group_id=group_id)
            
        medications = []
        for trade_name in queryset:
            medications.append({
                'id': trade_name.id,
                'trade_name': trade_name.name,
                'medication_name': trade_name.medication.name,
                'medication_id': trade_name.medication.id,
                'group': trade_name.medication_group.name if trade_name.medication_group else None,
                'release_form': trade_name.release_form.name if trade_name.release_form else None,
                'atc_code': trade_name.atc_code,
                'external_info_url': trade_name.external_info_url,
                'regimens_count': trade_name.medication.regimens.count()
            })
            
        return medications
    
    @staticmethod
    def search_medications(query: str) -> List[Dict]:
        """
        Поиск препаратов по названию (торговому или МНН).
        
        :param query: Поисковый запрос
        :return: Список найденных препаратов
        """
        queryset = TradeName.objects.select_related(
            'medication', 'medication_group', 'release_form'
        ).filter(
            Q(name__icontains=query) | 
            Q(medication__name__icontains=query)
        )[:20]  # Ограничиваем результаты
        
        return [
            {
                'id': tn.id,
                'trade_name': tn.name,
                'medication_name': tn.medication.name,
                'group': tn.medication_group.name if tn.medication_group else None,
                'release_form': tn.release_form.name if tn.release_form else None,
            }
            for tn in queryset
        ]


class RegimenService:
    """Сервис для работы со схемами применения препаратов."""
    
    @staticmethod
    def get_regimens_for_medication(medication_id: int) -> List[Dict]:
        """
        Получает все схемы применения для конкретного препарата.
        
        :param medication_id: ID препарата (МНН)
        :return: Список схем применения
        """
        regimens = Regimen.objects.filter(medication_id=medication_id).prefetch_related(
            'indications',
            'population_criteria',
            'dosing_instructions',
            'adjustments'
        )
        
        result = []
        for regimen in regimens:
            regimen_data = {
                'id': regimen.id,
                'name': regimen.name,
                'medication_name': regimen.medication.name,
                'notes': regimen.notes,
                'indications': [d.name for d in regimen.indications.all()],
                'population_criteria': [],
                'dosing_instructions': [],
                'adjustments': []
            }
            
            # Добавляем критерии пациентов
            for criteria in regimen.population_criteria.all():
                regimen_data['population_criteria'].append({
                    'name': criteria.name,
                    'age_range': f"{criteria.min_age_days or 0} - {criteria.max_age_days or '∞'} дней",
                    'weight_range': f"{criteria.min_weight_kg or 0} - {criteria.max_weight_kg or '∞'} кг"
                })
            
            # Добавляем инструкции по дозированию
            for instruction in regimen.dosing_instructions.all():
                regimen_data['dosing_instructions'].append({
                    'dose_type': instruction.get_dose_type_display(),
                    'dose_description': instruction.dose_description,
                    'frequency': instruction.frequency_description,
                    'duration': instruction.duration_description,
                    'route': instruction.route.name if instruction.route else None
                })
            
            # Добавляем корректировки
            for adjustment in regimen.adjustments.all():
                regimen_data['adjustments'].append({
                    'condition': adjustment.condition,
                    'adjustment': adjustment.adjustment_description
                })
            
            result.append(regimen_data)
            
        return result
    
    @staticmethod
    def get_regimens_by_diagnosis(diagnosis_id: int) -> List[Dict]:
        """
        Получает схемы применения для конкретного диагноза.
        
        :param diagnosis_id: ID диагноза
        :return: Список схем применения
        """
        regimens = Regimen.objects.filter(
            indications=diagnosis_id
        ).select_related('medication').prefetch_related(
            'indications', 'dosing_instructions'
        )
        
        return [
            {
                'id': regimen.id,
                'name': regimen.name,
                'medication_name': regimen.medication.name,
                'notes': regimen.notes,
                'indications': [ind.name for ind in regimen.indications.all()],
                'dosing_instructions': [
                    {
                        'dose_description': di.dose_description,
                        'frequency': di.frequency_description,
                        'duration': di.duration_description
                    }
                    for di in regimen.dosing_instructions.all()
                ]
            }
            for regimen in regimens
        ]


class PatientRecommendationService:
    """Сервис для подбора рекомендаций по препаратам для конкретного пациента."""
    
    @staticmethod
    def get_patient_recommendations(
        patient: Patient, 
        diagnosis: Optional[Diagnosis] = None,
        exclude_medication_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Подбирает подходящие схемы применения для пациента.
        
        :param patient: Объект пациента
        :param diagnosis: Диагноз (опционально)
        :param exclude_medication_ids: ID препаратов для исключения (аллергии)
        :return: Словарь с рекомендациями, сгруппированными по препаратам
        """
        if not patient or not patient.birth_date:
            return {}
        
        # Рассчитываем возраст пациента в днях
        age_in_days = (date.today() - patient.birth_date).days
        weight_kg = None  # Поле weight_kg отсутствует в модели Patient
        
        # Базовый запрос схем
        regimens_qs = Regimen.objects.select_related('medication').prefetch_related(
            'indications',
            'population_criteria',
            'dosing_instructions',
            'adjustments'
        )
        
        # Фильтруем по диагнозу
        if diagnosis:
            regimens_qs = regimens_qs.filter(indications=diagnosis)
        
        # Исключаем препараты с аллергией
        if exclude_medication_ids:
            regimens_qs = regimens_qs.exclude(medication_id__in=exclude_medication_ids)
        
        recommendations = defaultdict(list)
        
        for regimen in regimens_qs:
            # Проверяем подходящие критерии пациента
            suitable_criteria = []
            for criteria in regimen.population_criteria.all():
                if PatientRecommendationService._is_patient_suitable(criteria, age_in_days, weight_kg):
                    suitable_criteria.append(criteria)
            
            if suitable_criteria:
                # Формируем рекомендацию
                recommendation = {
                    'regimen_id': regimen.id,
                    'regimen_name': regimen.name,
                    'medication_name': regimen.medication.name,
                    'notes': regimen.notes,
                    'suitable_criteria': [
                        {
                            'name': criteria.name,
                            'age_range': f"{criteria.min_age_days or 0} - {criteria.max_age_days or '∞'} дней",
                            'weight_range': f"{criteria.min_weight_kg or 0} - {criteria.max_weight_kg or '∞'} кг"
                        }
                        for criteria in suitable_criteria
                    ],
                    'dosing_instructions': [
                        {
                            'dose_type': di.get_dose_type_display(),
                            'dose_description': di.dose_description,
                            'frequency': di.frequency_description,
                            'duration': di.duration_description,
                            'route': di.route.name if di.route else None
                        }
                        for di in regimen.dosing_instructions.all()
                    ],
                    'adjustments': [
                        {
                            'condition': adj.condition,
                            'adjustment': adj.adjustment_description
                        }
                        for adj in regimen.adjustments.all()
                    ]
                }
                
                # Группируем по названию препарата
                recommendations[regimen.medication.name].append(recommendation)
        
        return dict(recommendations)
    
    @staticmethod
    def _is_patient_suitable(criteria: PopulationCriteria, age_in_days: int, weight_kg: Optional[float]) -> bool:
        """
        Проверяет, подходит ли пациент под критерии.
        
        :param criteria: Критерии пациента
        :param age_in_days: Возраст пациента в днях
        :param weight_kg: Вес пациента в кг
        :return: True если пациент подходит под критерии
        """
        # Проверка по возрасту
        if criteria.min_age_days and age_in_days < criteria.min_age_days:
            return False
        if criteria.max_age_days and age_in_days > criteria.max_age_days:
            return False
        
        # Проверка по весу (если вес известен)
        if weight_kg:
            if criteria.min_weight_kg and weight_kg < criteria.min_weight_kg:
                return False
            if criteria.max_weight_kg and weight_kg > criteria.max_weight_kg:
                return False
        
        return True


class ReferenceDataService:
    """Сервис для работы со справочными данными."""
    
    @staticmethod
    def get_medication_groups() -> List[Dict]:
        """Получает список всех фармакологических групп."""
        groups = MedicationGroup.objects.all()
        return [
            {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'medications_count': group.medications.count()
            }
            for group in groups
        ]
    
    @staticmethod
    def get_release_forms() -> List[Dict]:
        """Получает список всех форм выпуска."""
        forms = ReleaseForm.objects.all()
        return [
            {
                'id': form.id,
                'name': form.name,
                'description': form.description,
                'medications_count': form.medications.count()
            }
            for form in forms
        ]
    
    @staticmethod
    def get_administration_methods() -> List[Dict]:
        """Получает список всех способов введения."""
        methods = AdministrationMethod.objects.all()
        return [
            {
                'id': method.id,
                'name': method.name,
                'description': method.description
            }
            for method in methods
        ]


# Функции для обратной совместимости (если нужно)
def get_medication_recommendations(patient, diagnosis=None, allergies_med_ids=None):
    """
    Устаревшая функция для обратной совместимости.
    Используйте PatientRecommendationService.get_patient_recommendations()
    """
    return PatientRecommendationService.get_patient_recommendations(
        patient=patient,
        diagnosis=diagnosis,
        exclude_medication_ids=allergies_med_ids
    )