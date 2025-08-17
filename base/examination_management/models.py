from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from encounters.models import Encounter
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition


class ExaminationPlan(models.Model):
    """
    Универсальный план обследования, который может быть привязан к любому объекту
    (encounter, department_stay, etc.)
    """
    PRIORITY_CHOICES = [
        ('normal', _('Обычный')),
        ('urgent', _('Срочный')),
        ('emergency', _('Экстренный')),
    ]
    
    name = models.CharField(_('Название плана'), max_length=255)
    description = models.TextField(_('Описание'), blank=True)
    
    # GenericForeignKey для связи с любым объектом (как в treatment_management)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey('content_type', 'object_id')
    
    # Оставляем encounter для обратной совместимости
    encounter = models.ForeignKey(
        Encounter, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name=_('Случай обращения'),
        related_name='examination_plans'
    )
    
    priority = models.CharField(
        _('Приоритет'), 
        max_length=20, 
        choices=PRIORITY_CHOICES, 
        default='normal'
    )
    is_active = models.BooleanField(_('Активен'), default=True)
    created_at = models.DateTimeField(_('Создан'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлен'), auto_now=True)
    
    class Meta:
        verbose_name = _('План обследования')
        verbose_name_plural = _('Планы обследования')
        ordering = ['-created_at']
    
    def __str__(self):
        if self.owner:
            return f"{self.name} ({self.owner})"
        elif self.encounter:
            return f"{self.name} - {self.encounter.patient.full_name}"
        return self.name
    
    def get_absolute_url(self):
        return reverse('examination_management:plan_detail', kwargs={'pk': self.pk})
    
    def get_owner_display(self):
        """Возвращает читаемое представление владельца"""
        if self.owner:
            if hasattr(self.owner, 'get_display_name'):
                return self.owner.get_display_name()
            return str(self.owner)
        elif self.encounter:
            return f"Случай: {self.encounter.patient.full_name}"
        return "Неизвестно"
    
    def get_owner_model_name(self):
        """Возвращает имя модели владельца для использования в шаблонах"""
        if self.owner:
            return self.owner._meta.model_name
        elif self.encounter:
            return 'encounter'
        return 'unknown'
    
    @classmethod
    def get_or_create_main_plan(cls, owner):
        """
        Получает или создает основной план обследования для указанного владельца
        """
        content_type = ContentType.objects.get_for_model(owner)
        
        # Пытаемся найти существующий основной план
        main_plan, created = cls.objects.get_or_create(
            content_type=content_type,
            object_id=owner.id,
            name="Основной план обследования",
            defaults={
                'description': 'Основной план обследования'
            }
        )
        
        return main_plan, created
    
    @property
    def lab_tests(self):
        """Получить все лабораторные исследования в плане"""
        return self.examinationlabtest_set.all()
    
    @property
    def instrumental_procedures(self):
        """Получить все инструментальные исследования в плане"""
        return self.examinationinstrumental_set.all()
    
    def get_lab_test_status(self, examination_lab_test):
        """
        Получить статус лабораторного исследования из связанного назначения
        """
        try:
            from treatment_assignments.models import LabTestAssignment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(ExaminationLabTest)
            assignment = LabTestAssignment.objects.filter(
                content_type=content_type,
                object_id=examination_lab_test.pk
            ).first()
            
            if assignment:
                # Проверяем наличие результатов
                has_results = assignment.results.exists()
                
                return {
                    'status': assignment.status,
                    'status_display': assignment.get_status_display(),
                    'completed_by': assignment.completed_by,
                    'end_date': assignment.end_date,
                    'rejection_reason': assignment.rejection_reason,
                    'assignment_id': assignment.pk,
                    'has_results': has_results
                }
        except Exception as e:
            print(f"Ошибка при получении статуса лабораторного исследования: {e}")
        
        return {
            'status': 'unknown',
            'status_display': 'Неизвестно',
            'completed_by': None,
            'end_date': None,
            'rejection_reason': None,
            'assignment_id': None,
            'has_results': False
        }
    
    def get_instrumental_procedure_status(self, examination_instrumental):
        """
        Получить статус инструментального исследования из связанного назначения
        """
        try:
            from treatment_assignments.models import InstrumentalProcedureAssignment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
            assignment = InstrumentalProcedureAssignment.objects.filter(
                content_type=content_type,
                object_id=examination_instrumental.pk
            ).first()
            
            if assignment:
                # Проверяем наличие результатов
                has_results = assignment.results.exists()
                
                return {
                    'status': assignment.status,
                    'status_display': assignment.get_status_display(),
                    'completed_by': assignment.completed_by,
                    'end_date': assignment.end_date,
                    'rejection_reason': assignment.rejection_reason,
                    'assignment_id': assignment.pk,
                    'has_results': has_results
                }
        except Exception as e:
            print(f"Ошибка при получении статуса инструментального исследования: {e}")
        
        return {
            'status': 'unknown',
            'status_display': 'Неизвестно',
            'completed_by': None,
            'end_date': None,
            'rejection_reason': None,
            'assignment_id': None,
            'has_results': False
        }
    
    def get_overall_progress(self):
        """
        Получить общий прогресс выполнения плана обследования
        """
        total_items = 0
        completed_items = 0
        rejected_items = 0
        active_items = 0
        
        # Подсчитываем лабораторные исследования
        for lab_test in self.lab_tests.all():
            total_items += 1
            status_info = self.get_lab_test_status(lab_test)
            if status_info['status'] == 'completed':
                completed_items += 1
            elif status_info['status'] == 'rejected':
                rejected_items += 1
            elif status_info['status'] == 'active':
                active_items += 1
        
        # Подсчитываем инструментальные исследования
        for instrumental in self.instrumental_procedures.all():
            total_items += 1
            status_info = self.get_instrumental_procedure_status(instrumental)
            if status_info['status'] == 'completed':
                completed_items += 1
            elif status_info['status'] == 'rejected':
                rejected_items += 1
            elif status_info['status'] == 'active':
                active_items += 1
        
        if total_items == 0:
            return {
                'total': 0,
                'completed': 0,
                'rejected': 0,
                'active': 0,
                'percentage': 0,
                'status': 'empty'
            }
        
        percentage = (completed_items / total_items) * 100
        
        # Определяем общий статус плана
        if completed_items == total_items:
            status = 'completed'
        elif rejected_items == total_items:
            status = 'rejected'
        elif completed_items > 0 or rejected_items > 0:
            status = 'in_progress'
        else:
            status = 'pending'
        
        return {
            'total': total_items,
            'completed': completed_items,
            'rejected': rejected_items,
            'active': active_items,
            'percentage': round(percentage, 1),
            'status': status
        }
    
    def get_patient(self):
        """
        Получает пациента из владельца плана
        """
        if self.owner:
            if hasattr(self.owner, 'patient'):
                return self.owner.patient
            elif hasattr(self.owner, 'get_patient'):
                return self.owner.get_patient()
        elif self.encounter:
            return self.encounter.patient
        return None


class ExaminationLabTest(models.Model):
    """
    Лабораторное исследование в плане обследования
    """
    examination_plan = models.ForeignKey(
        ExaminationPlan, 
        on_delete=models.CASCADE, 
        verbose_name=_('План обследования'),
        related_name='lab_tests'
    )
    lab_test = models.ForeignKey(
        LabTestDefinition, 
        on_delete=models.CASCADE, 
        verbose_name=_('Лабораторное исследование'),
        related_name='examination_lab_tests'
    )
    is_active = models.BooleanField(_('Активно'), default=True)
    instructions = models.TextField(_('Особые указания'), blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    class Meta:
        verbose_name = _('Лабораторное исследование в плане')
        verbose_name_plural = _('Лабораторные исследования в плане')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.lab_test.name} в плане {self.examination_plan.name}"
    
    def get_absolute_url(self):
        return reverse('examination_management:lab_test_detail', kwargs={'pk': self.pk})
    
    def get_lab_test_name(self):
        """Получить название лабораторного исследования"""
        return self.lab_test.name


class ExaminationInstrumental(models.Model):
    """
    Инструментальное исследование в плане обследования
    """
    examination_plan = models.ForeignKey(
        ExaminationPlan, 
        on_delete=models.CASCADE, 
        verbose_name=_('План обследования'),
        related_name='instrumental_procedures'
    )
    instrumental_procedure = models.ForeignKey(
        InstrumentalProcedureDefinition, 
        on_delete=models.CASCADE, 
        verbose_name=_('Инструментальное исследование'),
        related_name='examination_instrumentals'
    )
    is_active = models.BooleanField(_('Активно'), default=True)
    instructions = models.TextField(_('Особые указания'), blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    class Meta:
        verbose_name = _('Инструментальное исследование в плане')
        verbose_name_plural = _('Инструментальные исследования в плане')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.instrumental_procedure.name} в плане {self.examination_plan.name}"
    
    def get_absolute_url(self):
        return reverse('examination_management:instrumental_detail', kwargs={'pk': self.pk})
    
    def get_procedure_name(self):
        """Получить название процедуры"""
        return self.instrumental_procedure.name

# ============================================================================
# СИГНАЛЫ ДЛЯ АВТОМАТИЧЕСКОГО УДАЛЕНИЯ НАЗНАЧЕНИЙ
# ============================================================================

@receiver(post_delete, sender=ExaminationLabTest)
def delete_lab_test_assignment(sender, instance, **kwargs):
    """
    Автоматически удаляет связанное назначение лабораторного исследования
    при удалении записи из плана обследования
    """
    try:
        from treatment_assignments.models import LabTestAssignment
        from django.contrib.contenttypes.models import ContentType
        
        print(f"Сигнал post_delete для ExaminationLabTest {instance.pk} - {instance.lab_test.name}")
        
        # Получаем ContentType для ExaminationLabTest
        content_type = ContentType.objects.get_for_model(ExaminationLabTest)
        print(f"ContentType для ExaminationLabTest: {content_type}")
        
        # Ищем и удаляем связанное назначение
        assignment = LabTestAssignment.objects.filter(
            content_type=content_type,
            object_id=instance.pk
        ).first()
        
        if assignment:
            print(f"Найдено назначение {assignment.pk} для пациента {assignment.patient.full_name}")
            assignment.delete()
            print(f"✓ Автоматически удалено назначение лабораторного исследования {assignment.pk} для {instance.lab_test.name}")
        else:
            print(f"⚠ Связанное назначение для лабораторного исследования {instance.pk} не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка при автоматическом удалении назначения лабораторного исследования: {e}")


@receiver(post_delete, sender=ExaminationInstrumental)
def delete_instrumental_procedure_assignment(sender, instance, **kwargs):
    """
    Автоматически удаляет связанное назначение инструментального исследования
    при удалении записи из плана обследования
    """
    try:
        from treatment_assignments.models import InstrumentalProcedureAssignment
        from django.contrib.contenttypes.models import ContentType
        
        print(f"Сигнал post_delete для ExaminationInstrumental {instance.pk} - {instance.instrumental_procedure.name}")
        
        # Получаем ContentType для ExaminationInstrumental
        content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
        print(f"ContentType для ExaminationInstrumental: {content_type}")
        
        # Ищем и удаляем связанное назначение
        assignment = InstrumentalProcedureAssignment.objects.filter(
            content_type=content_type,
            object_id=instance.pk
        ).first()
        
        if assignment:
            print(f"Найдено назначение {assignment.pk} для пациента {assignment.patient.full_name}")
            assignment.delete()
            print(f"✓ Автоматически удалено назначение инструментального исследования {assignment.pk} для {instance.instrumental_procedure.name}")
        else:
            print(f"⚠ Связанное назначение для инструментального исследования {instance.pk} не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка при автоматическом удалении назначения инструментального исследования: {e}")


@receiver(post_delete, sender=ExaminationPlan)
def delete_plan_assignments(sender, instance, **kwargs):
    """
    Автоматически удаляет все связанные назначения при удалении плана обследования
    """
    try:
        from treatment_assignments.models import LabTestAssignment, InstrumentalProcedureAssignment
        from django.contrib.contenttypes.models import ContentType
        
        print(f"Сигнал post_delete для ExaminationPlan {instance.pk} - {instance.name}")
        
        # Получаем ContentType для ExaminationLabTest и ExaminationInstrumental
        lab_test_content_type = ContentType.objects.get_for_model(ExaminationLabTest)
        instrumental_content_type = ContentType.objects.get_for_model(ExaminationInstrumental)
        
        print(f"ContentType для ExaminationLabTest: {lab_test_content_type}")
        print(f"ContentType для ExaminationInstrumental: {instrumental_content_type}")
        
        # Удаляем все назначения лабораторных исследований из этого плана
        lab_assignments = LabTestAssignment.objects.filter(
            content_type=lab_test_content_type,
            object_id__in=instance.lab_tests.values_list('pk', flat=True)
        )
        lab_count = lab_assignments.count()
        if lab_count > 0:
            print(f"Найдено {lab_count} назначений лабораторных исследований для удаления")
            lab_assignments.delete()
            print(f"✓ Удалено {lab_count} назначений лабораторных исследований")
        
        # Удаляем все назначения инструментальных исследований из этого плана
        instrumental_assignments = InstrumentalProcedureAssignment.objects.filter(
            content_type=instrumental_content_type,
            object_id__in=instance.instrumental_procedures.values_list('pk', flat=True)
        )
        instrumental_count = instrumental_assignments.count()
        if instrumental_count > 0:
            print(f"Найдено {instrumental_count} назначений инструментальных исследований для удаления")
            instrumental_assignments.delete()
            print(f"✓ Удалено {instrumental_count} назначений инструментальных исследований")
        
        if lab_count > 0 or instrumental_count > 0:
            print(f"✓ Автоматически удалено {lab_count} лабораторных и {instrumental_count} инструментальных назначений при удалении плана {instance.pk}")
        else:
            print(f"ℹ Нет назначений для удаления при удалении плана {instance.pk}")
            
    except Exception as e:
        print(f"❌ Ошибка при автоматическом удалении назначений плана: {e}")
