from django.shortcuts import redirect
from django.contrib import messages
from .utils import redirect_to_schedule_settings


class ScheduleRedirectMixin:
    """
    Миксин для автоматического перенаправления на форму настройки расписания
    после успешного создания назначения
    """
    
    assignment_type = None  # Должен быть переопределен в дочернем классе
    
    def form_valid(self, form):
        """Переопределяем form_valid для перенаправления на настройку расписания"""
        response = super().form_valid(form)
        
        # Добавляем сообщение об успехе
        if not hasattr(self, 'success_message'):
            self.success_message = f'{self.model._meta.verbose_name} успешно создан'
        
        if self.success_message:
            messages.success(self.request, self.success_message)
        
        # Перенаправляем на форму настройки расписания
        if self.assignment_type:
            return redirect_to_schedule_settings(form.instance, self.assignment_type, self.request)
        
        return response


class MedicationScheduleRedirectMixin(ScheduleRedirectMixin):
    """Миксин для лекарств"""
    assignment_type = 'medication'


class LabTestScheduleRedirectMixin(ScheduleRedirectMixin):
    """Миксин для лабораторных исследований"""
    assignment_type = 'lab_test'


class ProcedureScheduleRedirectMixin(ScheduleRedirectMixin):
    """Миксин для процедур"""
    assignment_type = 'procedure' 