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
    План обследования пациента
    """
    PRIORITY_CHOICES = [
        ('normal', _('Обычный')),
        ('urgent', _('Срочный')),
        ('emergency', _('Экстренный')),
    ]
    
    name = models.CharField(_('Название плана'), max_length=255)
    description = models.TextField(_('Описание'), blank=True)
    encounter = models.ForeignKey(
        Encounter, 
        on_delete=models.CASCADE, 
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
        return f"{self.name} - {self.encounter.patient.full_name}"
    
    def get_absolute_url(self):
        return reverse('examination_management:plan_detail', kwargs={'pk': self.pk})
    
    @property
    def lab_tests(self):
        """Получить все лабораторные исследования в плане"""
        return self.examinationlabtest_set.all()
    
    @property
    def instrumental_procedures(self):
        """Получить все инструментальные исследования в плане"""
        return self.examinationinstrumental_set.all()


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
