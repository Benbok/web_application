from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import ExaminationPlan


class ExaminationPlanService:
    """
    Сервис для управления планами обследования
    """
    
    @staticmethod
    def create_examination_plan(owner, name, description='', priority='normal', is_active=True, created_by=None):
        """
        Создает новый план обследования для указанного владельца
        
        Args:
            owner: Объект-владелец (encounter, department_stay, etc.)
            name: Название плана
            description: Описание плана
            priority: Приоритет плана
            is_active: Активен ли план
            created_by: Создатель плана
        
        Returns:
            ExaminationPlan: Созданный план обследования
        """
        # Определяем тип владельца по имени модели и устанавливаем соответствующее поле
        owner_model_name = owner._meta.model_name if hasattr(owner, '_meta') else None
        if owner_model_name == 'patientdepartmentstatus':
            examination_plan = ExaminationPlan.objects.create(
                patient_department_status=owner,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        elif owner_model_name == 'encounter':
            examination_plan = ExaminationPlan.objects.create(
                encounter=owner,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        else:
            # Для обратной совместимости используем GenericForeignKey
            content_type = ContentType.objects.get_for_model(owner)
            examination_plan = ExaminationPlan.objects.create(
                content_type=content_type,
                object_id=owner.id,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        
        return examination_plan
    
    @staticmethod
    def get_examination_plans(owner):
        """
        Получает все планы обследования для указанного владельца
        
        Args:
            owner: Объект-владелец
        
        Returns:
            QuerySet: Планы обследования
        """
        # Определяем тип владельца по имени модели и используем соответствующее поле
        owner_model_name = owner._meta.model_name if hasattr(owner, '_meta') else None
        if owner_model_name == 'patientdepartmentstatus':
            return ExaminationPlan.objects.filter(patient_department_status=owner)
        elif owner_model_name == 'encounter':
            return ExaminationPlan.objects.filter(encounter=owner)
        else:
            # Для обратной совместимости используем GenericForeignKey
            content_type = ContentType.objects.get_for_model(owner)
            return ExaminationPlan.objects.filter(
                content_type=content_type,
                object_id=owner.id
            )
    
    @staticmethod
    def delete_examination_plan(examination_plan):
        """
        Удаляет план обследования и все связанные исследования
        
        Args:
            examination_plan: План обследования для удаления
        """
        with transaction.atomic():
            examination_plan.delete() 
from django.db import transaction
from .models import ExaminationPlan


class ExaminationPlanService:
    """
    Сервис для управления планами обследования
    """
    
    @staticmethod
    def create_examination_plan(owner, name, description='', priority='normal', is_active=True, created_by=None):
        """
        Создает новый план обследования для указанного владельца
        
        Args:
            owner: Объект-владелец (encounter, department_stay, etc.)
            name: Название плана
            description: Описание плана
            priority: Приоритет плана
            is_active: Активен ли план
            created_by: Создатель плана
        
        Returns:
            ExaminationPlan: Созданный план обследования
        """
        # Определяем тип владельца по имени модели и устанавливаем соответствующее поле
        owner_model_name = owner._meta.model_name if hasattr(owner, '_meta') else None
        if owner_model_name == 'patientdepartmentstatus':
            examination_plan = ExaminationPlan.objects.create(
                patient_department_status=owner,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        elif owner_model_name == 'encounter':
            examination_plan = ExaminationPlan.objects.create(
                encounter=owner,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        else:
            # Для обратной совместимости используем GenericForeignKey
            content_type = ContentType.objects.get_for_model(owner)
            examination_plan = ExaminationPlan.objects.create(
                content_type=content_type,
                object_id=owner.id,
                name=name,
                description=description,
                priority=priority,
                is_active=is_active,
                created_by=created_by
            )
        
        return examination_plan
    
    @staticmethod
    def get_examination_plans(owner):
        """
        Получает все планы обследования для указанного владельца
        
        Args:
            owner: Объект-владелец
        
        Returns:
            QuerySet: Планы обследования
        """
        # Определяем тип владельца по имени модели и используем соответствующее поле
        owner_model_name = owner._meta.model_name if hasattr(owner, '_meta') else None
        if owner_model_name == 'patientdepartmentstatus':
            return ExaminationPlan.objects.filter(patient_department_status=owner)
        elif owner_model_name == 'encounter':
            return ExaminationPlan.objects.filter(encounter=owner)
        else:
            # Для обратной совместимости используем GenericForeignKey
            content_type = ContentType.objects.get_for_model(owner)
            return ExaminationPlan.objects.filter(
                content_type=content_type,
                object_id=owner.id
            )
    
    @staticmethod
    def delete_examination_plan(examination_plan):
        """
        Удаляет план обследования и все связанные исследования
        
        Args:
            examination_plan: План обследования для удаления
        """
        with transaction.atomic():
            examination_plan.delete() 