from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import TreatmentPlan, TreatmentMedication
from pharmacy.models import Medication, Regimen, DosingInstruction
from pharmacy.services import PatientRecommendationService


class TreatmentPlanService:
    """
    Сервис для управления планами лечения
    """
    
    @staticmethod
    def create_treatment_plan(owner, name, description=''):
        """
        Создает новый план лечения для указанного владельца
        
        Args:
            owner: Объект-владелец (encounter, department_stay, etc.)
            name: Название плана
            description: Описание плана
        
        Returns:
            TreatmentPlan: Созданный план лечения
        """
        content_type = ContentType.objects.get_for_model(owner)
        
        treatment_plan = TreatmentPlan.objects.create(
            content_type=content_type,
            object_id=owner.id,
            name=name,
            description=description
        )
        
        return treatment_plan
    
    @staticmethod
    def get_treatment_plans(owner):
        """
        Получает все планы лечения для указанного владельца
        
        Args:
            owner: Объект-владелец
        
        Returns:
            QuerySet: Планы лечения
        """
        content_type = ContentType.objects.get_for_model(owner)
        return TreatmentPlan.objects.filter(
            content_type=content_type,
            object_id=owner.id
        )
    
    @staticmethod
    def delete_treatment_plan(treatment_plan):
        """
        Удаляет план лечения и все связанные лекарства
        
        Args:
            treatment_plan: План лечения для удаления
        """
        with transaction.atomic():
            treatment_plan.delete()


class TreatmentMedicationService:
    """
    Сервис для управления лекарствами в планах лечения
    """
    
    @staticmethod
    def add_medication_to_plan(treatment_plan, medication_data):
        """
        Добавляет лекарство в план лечения
        
        Args:
            treatment_plan: План лечения
            medication_data: Словарь с данными о лекарстве
        
        Returns:
            TreatmentMedication: Созданное лекарство
        """
        medication = TreatmentMedication.objects.create(
            treatment_plan=treatment_plan,
            **medication_data
        )
        
        return medication
    
    @staticmethod
    def get_medication_info(medication_id, patient=None, trade_name_id=None):
        """
        Получает информацию о лекарстве для автоматического заполнения полей
        
        Args:
            medication_id: ID лекарства
            patient: Пациент (для учета возрастной группы)
            trade_name_id: ID торгового наименования (для учета формы выпуска)
        
        Returns:
            dict: Информация о лекарства
        """
        try:
            medication = Medication.objects.get(id=medication_id)
        except Medication.DoesNotExist:
            return None
        
        # Базовая информация
        medication_info = {
            'id': medication.id,
            'name': medication.name,
            'description': getattr(medication, 'description', ''),
            'external_url': medication.external_info_url or '',
            'dosage': '',
            'frequency': '',
            'route': 'oral',
            'duration': '',
            'instructions': ''
        }
        
        # Получаем подходящую схему применения
        try:
            regimen = TreatmentMedicationService._get_best_regimen(medication, patient, trade_name_id)
            
            if regimen:
                # Ищем инструкции по дозировке
                dosing_instructions = DosingInstruction.objects.filter(regimen=regimen)
                
                if dosing_instructions.exists():
                    # Берем первую инструкцию (обычно основную)
                    dosing_instruction = dosing_instructions.first()
                    
                    medication_info.update({
                        'dosage': getattr(dosing_instruction, 'dose_description', '') or '',
                        'frequency': getattr(dosing_instruction, 'frequency_description', '') or '',
                        'route': TreatmentMedicationService._convert_route_to_choice(dosing_instruction.route) if dosing_instruction.route else 'oral',
                        'duration': getattr(dosing_instruction, 'duration_description', '') or '',
                        'instructions': getattr(regimen, 'notes', '') or ''
                    })
                    
                    medication_info['selected_regimen'] = {
                        'id': regimen.id,
                        'name': getattr(regimen, 'name', 'Схема применения')
                    }
        except Exception as e:
            # В случае ошибки просто возвращаем базовую информацию
            print(f"Ошибка при получении информации о лекарстве: {e}")
            pass
        
        return medication_info
    
    @staticmethod
    def _get_best_regimen(medication, patient, trade_name_id=None):
        """
        Выбирает лучшую схему применения для пациента с учетом возраста, популяционных критериев и формы выпуска
        
        Args:
            medication: Лекарство
            patient: Пациент
            trade_name_id: ID торгового наименования (для учета формы выпуска)
        
        Returns:
            Regimen: Лучшая схема применения
        """
        # Получаем все схемы для лекарства
        regimens = Regimen.objects.filter(medication=medication)
        
        if not regimens.exists():
            return None
        
        # Если указано торговое наименование, получаем форму выпуска
        release_form = None
        if trade_name_id:
            try:
                from pharmacy.models import TradeName
                trade_name = TradeName.objects.get(id=trade_name_id)
                release_form = trade_name.release_form
            except TradeName.DoesNotExist:
                pass
        
        # Если пациент не указан, возвращаем первую схему с инструкциями
        if not patient:
            # Если есть форма выпуска, ищем схему с соответствующей дозировкой
            if release_form:
                for regimen in regimens:
                    if DosingInstruction.objects.filter(regimen=regimen).exists():
                        # Проверяем, подходит ли схема для данной формы выпуска
                        if TreatmentMedicationService._is_regimen_suitable_for_form(regimen, release_form):
                            return regimen
            
            # Если не найдено подходящей схемы, возвращаем первую с инструкциями
            for regimen in regimens:
                if DosingInstruction.objects.filter(regimen=regimen).exists():
                    return regimen
            return regimens.first()
        
        # Получаем возраст пациента в днях
        try:
            age_years = patient.get_age() if hasattr(patient, 'get_age') else None
            age_days = age_years * 365 if age_years else None
        except:
            age_days = None
        
        # Получаем вес пациента (пока не реализовано в модели Patient)
        weight_kg = None
        
        # Сначала ищем схемы, которые точно подходят по критериям и форме выпуска
        best_regimen = None
        best_score = 0
        
        for regimen in regimens:
            # Проверяем, есть ли инструкции по дозировке
            if not DosingInstruction.objects.filter(regimen=regimen).exists():
                continue
            
            # Если есть форма выпуска, проверяем соответствие
            if release_form and not TreatmentMedicationService._is_regimen_suitable_for_form(regimen, release_form):
                continue
            
            # Получаем критерии для этой схемы
            population_criteria = regimen.population_criteria.all()
            
            if not population_criteria.exists():
                # Если нет критериев, считаем подходящей
                score = 1
            else:
                # Проверяем соответствие критериям
                score = TreatmentMedicationService._calculate_criteria_match(
                    population_criteria, age_days, weight_kg
                )
            
            if score > best_score:
                best_score = score
                best_regimen = regimen
        
        # Если найдена подходящая схема, возвращаем её
        if best_regimen:
            return best_regimen
        
        # Если не найдено подходящих схем, возвращаем первую с инструкциями
        for regimen in regimens:
            if DosingInstruction.objects.filter(regimen=regimen).exists():
                return regimen
        
        # Если ничего не найдено, возвращаем первую схему
        return regimens.first()
    
    @staticmethod
    def _check_criteria_match(criteria, age, weight):
        """
        Проверяет соответствие критериев пациента
        
        Args:
            criteria: Критерии пациента
            age: Возраст пациента
            weight: Вес пациента
        
        Returns:
            bool: Соответствует ли пациент критериям
        """
        # Здесь можно добавить логику проверки критериев
        # Пока возвращаем True для упрощения
        return True
    
    @staticmethod
    def _calculate_criteria_match(population_criteria, age_days, weight_kg):
        """
        Рассчитывает соответствие пациента популяционным критериям
        
        Args:
            population_criteria: QuerySet критериев
            age_days: Возраст пациента в днях
            weight_kg: Вес пациента в кг
        
        Returns:
            float: Оценка соответствия (0-1, где 1 - полное соответствие)
        """
        if not population_criteria.exists():
            return 0.0
        
        best_match = 0.0
        
        for criteria in population_criteria:
            match_score = 0.0
            criteria_count = 0
            
            # Проверяем соответствие по возрасту
            if age_days is not None:
                criteria_count += 1
                age_match = True
                
                if criteria.min_age_days and age_days < criteria.min_age_days:
                    age_match = False
                if criteria.max_age_days and age_days > criteria.max_age_days:
                    age_match = False
                
                if age_match:
                    match_score += 1.0
            
            # Проверяем соответствие по весу
            if weight_kg is not None:
                criteria_count += 1
                weight_match = True
                
                if criteria.min_weight_kg and weight_kg < criteria.min_weight_kg:
                    weight_match = False
                if criteria.max_weight_kg and weight_kg > criteria.max_weight_kg:
                    weight_match = False
                
                if weight_match:
                    match_score += 1.0
            
            # Если нет критериев для проверки, считаем подходящим
            if criteria_count == 0:
                match_score = 1.0
                criteria_count = 1
            
            # Рассчитываем общий балл для этого критерия
            criteria_score = match_score / criteria_count if criteria_count > 0 else 0.0
            
            # Обновляем лучший результат
            if criteria_score > best_match:
                best_match = criteria_score
        
        return best_match
    
    @staticmethod
    def _is_regimen_suitable_for_form(regimen, release_form):
        """
        Проверяет, подходит ли схема применения для данной формы выпуска
        
        Args:
            regimen: Схема применения
            release_form: Форма выпуска
        
        Returns:
            bool: Подходит ли схема для формы выпуска
        """
        if not release_form:
            return True
        
        regimen_name = regimen.name.lower()
        form_name = release_form.name.lower()
        
        # Маппинг форм выпуска на ключевые слова в названиях схем
        form_keywords = {
            'гель': ['гель', 'гелевая'],
            'мазь': ['мазь', 'мазевая'],
            'суппозитории': ['суппозитории', 'ректально', 'свечи'],
            'таблетки': ['таблетки', 'перорально', 'внутрь'],
            'капсулы': ['капсулы', 'перорально', 'внутрь'],
            'раствор': ['раствор', 'инъекции', 'внутривенно', 'внутримышечно'],
            'порошок': ['порошок', 'инъекции', 'внутривенно', 'внутримышечно'],
        }
        
        # Определяем тип формы выпуска
        form_type = None
        for key, keywords in form_keywords.items():
            if any(keyword in form_name for keyword in keywords):
                form_type = key
                break
        
        if not form_type:
            return True  # Если не можем определить тип, считаем подходящей
        
        # Проверяем соответствие схемы типу формы
        for keyword in form_keywords[form_type]:
            if keyword in regimen_name:
                return True
        
        return False
    
    @staticmethod
    def _convert_route_to_choice(administration_method):
        """
        Преобразует AdministrationMethod в выбор для TreatmentMedication.route
        
        Args:
            administration_method: AdministrationMethod объект
        
        Returns:
            str: Соответствующий выбор из ROUTE_CHOICES
        """
        if not administration_method:
            return 'oral'
        
        method_name = administration_method.name.lower()
        
        # Маппинг названий способов введения
        route_mapping = {
            'перорально': 'oral',
            'внутримышечно': 'intramuscular',
            'внутривенно': 'intravenous',
            'подкожно': 'subcutaneous',
            'наружно': 'topical',
            'ингаляционно': 'inhalation',
            'ректально': 'rectal',
            'oral': 'oral',
            'intramuscular': 'intramuscular',
            'intravenous': 'intravenous',
            'subcutaneous': 'subcutaneous',
            'topical': 'topical',
            'inhalation': 'inhalation',
            'rectal': 'rectal',
        }
        
        # Ищем точное совпадение
        for key, value in route_mapping.items():
            if key in method_name:
                return value
        
        # Если не найдено, возвращаем 'other'
        return 'other'


class TreatmentRecommendationService:
    """
    Сервис для получения рекомендаций по лечению
    """
    
    @staticmethod
    def get_medication_recommendations(diagnosis_code, patient=None):
        """
        Получает рекомендации по лекарствам для диагноза
        
        Args:
            diagnosis_code: Код диагноза
            patient: Пациент
        
        Returns:
            list: Список рекомендованных лекарств
        """
        try:
            # Получаем диагноз из pharmacy
            from pharmacy.models import Diagnosis
            diagnosis = Diagnosis.objects.get(code=diagnosis_code)
        except Diagnosis.DoesNotExist:
            return []
        
        # Используем существующий сервис рекомендаций
        recommendations = PatientRecommendationService.get_patient_recommendations(
            patient=patient,
            diagnosis=diagnosis
        )
        
        # Преобразуем результат в список для совместимости с шаблоном
        result = []
        for medication_name, medication_recommendations in recommendations.items():
            for recommendation in medication_recommendations:
                result.append({
                    'name': medication_name,
                    'dosage': recommendation.get('dosing_instructions', [{}])[0].get('dose_description', ''),
                    'frequency': recommendation.get('dosing_instructions', [{}])[0].get('frequency', ''),
                    'route': recommendation.get('dosing_instructions', [{}])[0].get('route', ''),
                    'duration': recommendation.get('dosing_instructions', [{}])[0].get('duration', ''),
                    'notes': recommendation.get('notes', '')
                })
        
        return result 