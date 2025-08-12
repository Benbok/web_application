from django.db import models
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json


def redirect_to_treatment_management(request, **kwargs):
    """
    Функция для перенаправления старых URLs лечения на новое приложение treatment_management
    """
    # Определяем тип запроса и соответствующий URL в treatment_management
    path = request.path
    
    if 'treatment-plans' in path:
        if '/add/' in path:
            # Создание плана лечения
            encounter_pk = kwargs.get('encounter_pk')
            return redirect('treatment_management:plan_create', 
                          owner_model='encounter', owner_id=encounter_pk)
        elif '/delete/' in path:
            # Удаление плана лечения
            plan_pk = kwargs.get('pk')
            return redirect('treatment_management:plan_delete', pk=plan_pk)
        elif '/medications/add/' in path:
            # Добавление лекарства
            plan_pk = kwargs.get('treatment_plan_pk')
            return redirect('treatment_management:medication_create', plan_pk=plan_pk)
        else:
            # Список или детали плана лечения
            encounter_pk = kwargs.get('encounter_pk') or kwargs.get('pk')
            if encounter_pk:
                return redirect('treatment_management:plan_list', 
                              owner_model='encounter', owner_id=encounter_pk)
            else:
                plan_pk = kwargs.get('pk')
                return redirect('treatment_management:plan_detail', pk=plan_pk)
    
    elif 'medications' in path:
        if '/edit/' in path:
            # Редактирование лекарства
            medication_pk = kwargs.get('pk')
            return redirect('treatment_management:medication_update', pk=medication_pk)
        elif '/delete/' in path:
            # Удаление лекарства
            medication_pk = kwargs.get('pk')
            return redirect('treatment_management:medication_delete', pk=medication_pk)
    
    elif 'quick-add' in path:
        # Быстрое добавление лекарства
        plan_pk = kwargs.get('plan_pk')
        medication_name = kwargs.get('medication_name')
        if medication_name:
            return redirect('treatment_management:quick_add_medication_by_name', 
                          plan_pk=plan_pk, medication_name=medication_name)
        else:
            return redirect('treatment_management:quick_add_medication', plan_pk=plan_pk)
    
    elif 'api/medication-info' in path or 'api/trade-name-info' in path or 'api/treatment-regimens' in path or 'api/patient-recommendations' in path:
        # AJAX endpoints для информации о лекарствах и схемах лечения
        # Перенаправляем на соответствующие endpoints в treatment_management
        if 'medication-info' in path:
            medication_id = kwargs.get('medication_id')
            return redirect('treatment_management:medication_info', medication_id=medication_id)
        elif 'trade-name-info' in path:
            trade_name_id = kwargs.get('trade_name_id')
            return redirect('treatment_management:trade_name_info', trade_name_id=trade_name_id)
        else:
            # Для остальных AJAX endpoints просто перенаправляем на главную страницу
            return redirect('patients:home')
    
    # Если не удалось определить URL, перенаправляем на главную страницу
    return redirect('patients:home')

from .models import Encounter, EncounterDiagnosis
from .services.encounter_service import EncounterService
from patients.models import Patient
from .forms import (
    EncounterForm, EncounterCloseForm, EncounterUpdateForm, EncounterReopenForm, 
    EncounterUndoForm, EncounterDiagnosisForm, EncounterDiagnosisAdvancedForm
)
from departments.models import Department, PatientDepartmentStatus
from diagnosis.models import Diagnosis


class EncounterDetailView(DetailView):
    model = Encounter
    template_name = 'encounters/detail.html'
    context_object_name = 'encounter'

    def get_queryset(self):
        """Оптимизируем queryset для избежания N+1 запросов"""
        return Encounter.objects.select_related(
            'patient',
            'doctor',
            'transfer_to_department'
        ).prefetch_related(
            'documents',
            'diagnoses__diagnosis',
            'treatment_plans__medications__medication',
            'department_transfer_records'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        
        # Используем сервис для получения деталей
        service = EncounterService(encounter)
        details = service.get_encounter_details()
        
        context['documents'] = details['documents']
        context['encounter_number'] = details['encounter_number']
        context['title'] = f'Обращение #{context["encounter_number"]}'
        
        # Добавляем информацию о диагнозах
        all_diagnoses = encounter.diagnoses.all().select_related('diagnosis')
        context['main_diagnosis'] = all_diagnoses.filter(diagnosis_type='main').first()
        context['complications'] = all_diagnoses.filter(diagnosis_type='complication')
        context['comorbidities'] = all_diagnoses.filter(diagnosis_type='comorbidity')
        
        # Добавляем информацию о планах лечения
        from treatment_management.models import TreatmentPlan
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(encounter)
        treatment_plans = TreatmentPlan.objects.filter(
            content_type=content_type,
            object_id=encounter.id
        )
        context['treatment_plans'] = treatment_plans
        
        return context


class EncounterCreateView(CreateView):
    model = Encounter
    form_class = EncounterForm
    template_name = 'encounters/form.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
    
    def form_valid(self, form):
        form.instance.patient = self.patient
        form.instance.doctor = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Обращение успешно создано')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['title'] = 'Создать обращение'
        return context
    
    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterUpdateView(UpdateView):
    model = Encounter
    form_class = EncounterUpdateForm
    template_name = 'encounters/form.html'
    
    def get_queryset(self):
        return Encounter.objects.select_related('patient', 'doctor')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['title'] = 'Редактировать обращение'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Обращение успешно обновлено')
        return response
    
    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDiagnosisView(UpdateView):
    """Представление для установки диагноза в случае обращения"""
    model = Encounter
    form_class = EncounterDiagnosisForm
    template_name = 'encounters/diagnosis_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Установить диагноз'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Диагноз успешно установлен')
        return response
    
    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDiagnosisAdvancedView(DetailView):
    """Представление для работы с расширенной структурой диагнозов"""
    model = Encounter
    template_name = 'encounters/diagnosis_advanced.html'
    context_object_name = 'encounter'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Диагнозы'
        context['patient'] = self.object.patient
        
        # Получаем все диагнозы
        all_diagnoses = self.object.diagnoses.all().select_related('diagnosis')
        

        
        # Разделяем по типам
        context['main_diagnosis'] = all_diagnoses.filter(diagnosis_type='main').first()
        context['complications'] = all_diagnoses.filter(diagnosis_type='complication')
        context['comorbidities'] = all_diagnoses.filter(diagnosis_type='comorbidity')
        
        return context


class EncounterDiagnosisCreateView(CreateView):
    """Представление для создания нового диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_create.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['encounter'] = self.encounter
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Диагноз успешно добавлен')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.encounter
        context['patient'] = self.encounter.patient
        context['title'] = 'Добавить диагноз'
        return context
    
    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.encounter.pk})


class EncounterDiagnosisUpdateView(UpdateView):
    """Представление для редактирования диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_edit.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['encounter'] = self.object.encounter
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['title'] = 'Редактировать диагноз'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Диагноз успешно обновлен')
        return response
    
    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.object.encounter.pk})


class EncounterDiagnosisDeleteView(DeleteView):
    """Представление для удаления диагноза"""
    model = EncounterDiagnosis
    template_name = 'encounters/diagnosis_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['title'] = 'Удалить диагноз'
        return context
    
    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.object.encounter.pk})


class EncounterDeleteView(DeleteView):
    model = Encounter
    template_name = 'encounters/confirm_delete.html'

    def get_context_data(self, **kwargs):
        """Добавляем номер обращения для страницы подтверждения."""
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        context['encounter_number'] = Encounter.objects.filter(
            patient_id=encounter.patient_id,
            date_start__lt=encounter.date_start
        ).count() + 1
        return context
    
    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})
    
class EncounterCloseView(UpdateView):
    model = Encounter
    form_class = EncounterCloseForm
    template_name = 'encounters/close_form.html'

    def get_object(self, queryset=None):
        obj = get_object_or_404(Encounter, pk=self.kwargs['pk'], is_active=True)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Завершить обращение'
        context['encounter'] = self.get_object()
        context['encounter_number'] = Encounter.objects.filter(
            patient_id=self.get_object().patient_id,
            date_start__lt=self.get_object().date_start
        ).count() + 1
        return context

    def form_valid(self, form):
        encounter = self.get_object()
        
        try:
            # Используем новую форму с Command Pattern
            form.save(user=self.request.user)
            messages.success(self.request, "Случай обращения успешно закрыт.")
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f"Ошибка при закрытии: {e}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})
    
class EncounterReopenView(View):
    """
    Представление для возврата случая обращения в активное состояние.
    Обрабатывает POST-запрос для изменения состояния.
    """
    def post(self, request, pk, *args, **kwargs):
        encounter = get_object_or_404(Encounter, pk=pk)

        if encounter.is_active:
            messages.warning(request, "Случай обращения уже активен.")
            return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))

        # Здесь также можно добавить проверку прав доступа
        # if not request.user.has_perm('encounters.can_reopen_encounter'):
        #     messages.error(request, "У вас нет прав для активации случая обращения.")
        #     return HttpResponseForbidden()

        # Используем сервис с Command Pattern
        service = EncounterService(encounter)
        if service.reopen_encounter(user=request.user):
            messages.success(request, "Случай обращения успешно возвращен в активное состояние.")
        else:
            messages.error(request, "Не удалось вернуть случай обращения в активное состояние.")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))


class EncounterUndoView(View):
    """
    Представление для отмены последней операции.
    Обрабатывает POST-запрос для отмены операции.
    """
    def post(self, request, pk, *args, **kwargs):
        encounter = get_object_or_404(Encounter, pk=pk)

        # Используем сервис для отмены операции
        service = EncounterService(encounter)
        if service.undo_last_operation():
            messages.success(request, "Последняя операция успешно отменена.")
        else:
            messages.error(request, "Не удалось отменить последнюю операцию.")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))


class TestJavaScriptView(View):
    """Простое представление для тестирования JavaScript"""
    
    def get(self, request):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        
        html_content = render_to_string('encounters/test_js.html')
        return HttpResponse(html_content)