from typing import List, Dict, Optional
from django.db.models import Q

from ..models import Encounter, TreatmentPlan, TreatmentMedication
from pharmacy.services import PatientRecommendationService
from pharmacy.models import Medication, TradeName


class TreatmentPlanService:
    """Сервис для работы с планами лечения"""
    
    @staticmethod
    def get_medication_recommendations(encounter: Encounter) -> Dict:
        """
        Получает рекомендации по лекарствам для случая обращения
        
        :param encounter: Случай обращения
        :return: Словарь с рекомендациями
        """
        # Получаем основной диагноз
        main_diagnosis = encounter.get_main_diagnosis()
        if not main_diagnosis:
            return {
                'error': 'Основной диагноз не установлен',
                'recommendations': []
            }
        
        # Получаем диагноз из справочника
        diagnosis = main_diagnosis.diagnosis
        if not diagnosis:
            return {
                'error': 'Основной диагноз не выбран из справочника',
                'recommendations': []
            }
        
        # Находим соответствующий диагноз в pharmacy app
        from pharmacy.models import Diagnosis as PharmacyDiagnosis
        pharmacy_diagnosis = PharmacyDiagnosis.objects.filter(code=diagnosis.code).first()
        print(f"DEBUG: Диагноз из diagnosis: {diagnosis.code} - {diagnosis.name}")
        print(f"DEBUG: Диагноз из pharmacy: {pharmacy_diagnosis.code if pharmacy_diagnosis else 'Не найден'} - {pharmacy_diagnosis.name if pharmacy_diagnosis else 'Не найден'}")
        
        if not pharmacy_diagnosis:
            return {
                'error': f'Диагноз {diagnosis.code} не найден в справочнике pharmacy',
                'recommendations': []
            }
        
        # Получаем рекомендации из pharmacy
        pharmacy_recommendations = PatientRecommendationService.get_patient_recommendations(
            patient=encounter.patient,
            diagnosis=pharmacy_diagnosis
        )
        
        print(f"DEBUG: pharmacy_recommendations keys: {list(pharmacy_recommendations.keys())}")
        print(f"DEBUG: pharmacy_recommendations values: {list(pharmacy_recommendations.values())}")
        
        # Преобразуем формат рекомендаций
        recommendations = []
        for medication_name, regimens in pharmacy_recommendations.items():
            for regimen in regimens:
                # Получаем информацию о лекарстве
                medication = regimen.get('medication_name', medication_name)
                
                # Ищем препарат в базе данных по названию
                medication_obj = None
                if medication:
                    # Поиск по точному названию
                    medication_obj = Medication.objects.filter(name__iexact=medication).first()
                    if not medication_obj:
                        # Поиск по частичному совпадению
                        medication_obj = Medication.objects.filter(name__icontains=medication).first()
                
                # Формируем рекомендацию
                recommendation = {
                    'medication': {
                        'id': medication_obj.id if medication_obj else None,
                        'name': medication
                    },
                    'regimen': {
                        'name': regimen.get('regimen_name', ''),
                        'dosage': '',
                        'frequency': '',
                        'route': 'oral',
                        'duration': '',
                        'instructions': ''
                    }
                }
                
                # Добавляем информацию о дозировке
                if regimen.get('dosing_instructions'):
                    for dose in regimen['dosing_instructions']:
                        recommendation['regimen']['dosage'] = dose.get('dose_description', '')
                        recommendation['regimen']['frequency'] = dose.get('frequency', '')
                        if dose.get('route'):
                            recommendation['regimen']['route'] = dose['route']
                        break  # Берем первую дозировку
                
                recommendations.append(recommendation)
        
        return {
            'recommendations': recommendations
        }
    
    @staticmethod
    def search_medications(query: str) -> List[Dict]:
        """
        Поиск лекарств по названию
        
        :param query: Поисковый запрос
        :return: Список найденных лекарств
        """
        # Поиск по торговым названиям
        trade_names = TradeName.objects.filter(
            Q(name__icontains=query) | 
            Q(medication__name__icontains=query)
        ).select_related('medication', 'medication_group', 'release_form')[:10]
        
        results = []
        for tn in trade_names:
            results.append({
                'id': tn.medication.id,  # Используем ID МНН
                'trade_name': tn.name,
                'medication_name': tn.medication.name,
                'group': tn.medication_group.name if tn.medication_group else None,
                'release_form': tn.release_form.name if tn.release_form else None,
                'display_name': f"{tn.name} ({tn.medication.name})"
            })
        
        return results
    
    @staticmethod
    def get_medication_details(medication_id: int) -> Optional[Dict]:
        """
        Получает детальную информацию о лекарстве
        
        :param medication_id: ID лекарства
        :return: Словарь с информацией о лекарстве
        """
        try:
            medication = Medication.objects.get(id=medication_id)
            trade_names = TradeName.objects.filter(medication=medication).select_related(
                'medication_group', 'release_form'
            )
            
            return {
                'id': medication.id,
                'name': medication.name,
                'trade_names': [
                    {
                        'name': tn.name,
                        'group': tn.medication_group.name if tn.medication_group else None,
                        'release_form': tn.release_form.name if tn.release_form else None,
                    }
                    for tn in trade_names
                ]
            }
        except Medication.DoesNotExist:
            return None
    
    @staticmethod
    def create_treatment_plan_with_recommendations(
        encounter: Encounter, 
        name: str, 
        description: str = ''
    ) -> TreatmentPlan:
        """
        Создает план лечения с автоматическими рекомендациями
        
        :param encounter: Случай обращения
        :param name: Название плана лечения
        :param description: Описание плана лечения
        :return: Созданный план лечения
        """
        # Создаем план лечения
        treatment_plan = TreatmentPlan.objects.create(
            encounter=encounter,
            name=name,
            description=description
        )
        
        # Получаем рекомендации
        recommendations = TreatmentPlanService.get_medication_recommendations(encounter)
        
        # Если есть ошибка, возвращаем план без лекарств
        if 'error' in recommendations:
            return treatment_plan
        
        # Добавляем рекомендованные лекарства
        for recommendation in recommendations.get('recommendations', []):
            medication_data = recommendation.get('medication', {})
            regimen_data = recommendation.get('regimen', {})
            
            if medication_data and regimen_data:
                # Ищем лекарство по названию
                medication_name = medication_data.get('name', '')
                medication = None
                if medication_name:
                    medication = Medication.objects.filter(name__icontains=medication_name).first()
                
                # Создаем запись о лекарстве
                TreatmentMedication.objects.create(
                    treatment_plan=treatment_plan,
                    medication=medication,  # Может быть None для custom_medication
                    custom_medication=medication_name if not medication else '',
                    dosage=regimen_data.get('dosage', ''),
                    frequency=regimen_data.get('frequency', ''),
                    route=regimen_data.get('route', 'oral'),
                    duration=regimen_data.get('duration', ''),
                    instructions=regimen_data.get('instructions', '')
                )
        
        return treatment_plan 