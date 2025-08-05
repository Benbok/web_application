from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView
)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import TreatmentPlan, TreatmentMedication
from .forms import TreatmentPlanForm, TreatmentMedicationForm, QuickAddMedicationForm
from .services import (
    TreatmentPlanService, TreatmentMedicationService, TreatmentRecommendationService
)
from patients.models import Patient


class TreatmentPlanListView(LoginRequiredMixin, ListView):
    """
    Список планов лечения для указанного владельца
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_list.html'
    context_object_name = 'treatment_plans'
    
    def get_queryset(self):
        # Получаем владельца из URL параметров
        owner_model = self.kwargs.get('owner_model')
        owner_id = self.kwargs.get('owner_id')
        
        # Получаем ContentType для модели владельца
        content_type = ContentType.objects.get(model=owner_model)
        owner_class = content_type.model_class()
        owner = get_object_or_404(owner_class, id=owner_id)
        
        # Сохраняем владельца в контексте
        self.owner = owner
        
        return TreatmentPlanService.get_treatment_plans(owner)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
        
        # Получаем пациента (если владелец имеет связь с пациентом)
        if hasattr(self.owner, 'patient'):
            context['patient'] = self.owner.patient
        elif hasattr(self.owner, 'get_patient'):
            context['patient'] = self.owner.get_patient()
        
        # Получаем рекомендации по лечению (если есть диагноз)
        if hasattr(self.owner, 'get_main_diagnosis_for_recommendations'):
            main_diagnosis = self.owner.get_main_diagnosis_for_recommendations()
            if main_diagnosis and context.get('patient'):
                recommendations = TreatmentRecommendationService.get_medication_recommendations(
                    main_diagnosis.code, context.get('patient')
                )
                context['recommendations'] = recommendations
        
        return context


class TreatmentPlanCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового плана лечения
    """
    model = TreatmentPlan
    form_class = TreatmentPlanForm
    template_name = 'treatment_management/plan_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Получаем владельца из URL параметров
        owner_model = self.kwargs.get('owner_model')
        owner_id = self.kwargs.get('owner_id')
        
        content_type = ContentType.objects.get(model=owner_model)
        owner_class = content_type.model_class()
        self.owner = get_object_or_404(owner_class, id=owner_id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Создаем план лечения через сервис
        treatment_plan = TreatmentPlanService.create_treatment_plan(
            owner=self.owner,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description']
        )
        
        messages.success(self.request, _('План лечения успешно создан'))
        return redirect('treatment_management:plan_detail', 
                       owner_model=self.kwargs['owner_model'],
                       owner_id=self.kwargs['owner_id'],
                       pk=treatment_plan.pk)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Передаем owner в форму для валидации
        kwargs['owner'] = self.owner
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
        context['title'] = _('Создать план лечения')
        return context


class TreatmentPlanDetailView(LoginRequiredMixin, DetailView):
    """
    Детальный просмотр плана лечения
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_detail.html'
    context_object_name = 'treatment_plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.object.owner
        context['owner_model'] = self.object.owner._meta.model_name
        context['medications'] = self.object.medications.all()
        
        # Получаем пациента
        if hasattr(self.object.owner, 'patient'):
            context['patient'] = self.object.owner.patient
        elif hasattr(self.object.owner, 'get_patient'):
            context['patient'] = self.object.owner.get_patient()
        
        return context


class TreatmentPlanDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление плана лечения
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.object.owner
        context['owner_model'] = self.object.owner._meta.model_name
        context['medications'] = self.object.medications.all()
        context['title'] = _('Удалить план лечения')
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_list',
                      kwargs={
                          'owner_model': self.object.owner._meta.model_name,
                          'owner_id': self.object.owner.id
                      })


class TreatmentMedicationCreateView(LoginRequiredMixin, CreateView):
    """
    Добавление лекарства в план лечения
    """
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'treatment_management/medication_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)
        messages.success(self.request, _('Лекарство успешно добавлено в план лечения'))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        context['owner'] = self.treatment_plan.owner
        context['owner_model'] = self.treatment_plan.owner._meta.model_name
        context['title'] = _('Добавить лекарство')
        
        # Получаем пациента
        if hasattr(self.treatment_plan.owner, 'patient'):
            context['patient'] = self.treatment_plan.owner.patient
        elif hasattr(self.treatment_plan.owner, 'get_patient'):
            context['patient'] = self.treatment_plan.owner.get_patient()
        
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.treatment_plan.owner._meta.model_name,
                          'owner_id': self.treatment_plan.owner.id,
                          'pk': self.treatment_plan.pk
                      })


class TreatmentMedicationUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование лекарства в плане лечения
    """
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'treatment_management/medication_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['owner'] = self.object.treatment_plan.owner
        context['owner_model'] = self.object.treatment_plan.owner._meta.model_name
        context['title'] = _('Редактировать лекарство')
        
        # Получаем пациента
        if hasattr(self.object.treatment_plan.owner, 'patient'):
            context['patient'] = self.object.treatment_plan.owner.patient
        elif hasattr(self.object.treatment_plan.owner, 'get_patient'):
            context['patient'] = self.object.treatment_plan.owner.get_patient()
        
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.object.treatment_plan.owner._meta.model_name,
                          'owner_id': self.object.treatment_plan.owner.id,
                          'pk': self.object.treatment_plan.pk
                      })


class TreatmentMedicationDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление лекарства из плана лечения
    """
    model = TreatmentMedication
    template_name = 'treatment_management/medication_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['owner'] = self.object.treatment_plan.owner
        context['owner_model'] = self.object.treatment_plan.owner._meta.model_name
        context['title'] = _('Удалить лекарство')
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.object.treatment_plan.owner._meta.model_name,
                          'owner_id': self.object.treatment_plan.owner.id,
                          'pk': self.object.treatment_plan.pk
                      })


class QuickAddMedicationView(LoginRequiredMixin, CreateView):
    """
    Быстрое добавление рекомендованного лекарства
    """
    model = TreatmentMedication
    form_class = QuickAddMedicationForm
    template_name = 'treatment_management/quick_add_medication.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        self.recommended_medication = None
        
        # Получаем рекомендованное лекарство (если указано)
        medication_name = self.kwargs.get('medication_name')
        if medication_name:
            # Создаем объект с именем лекарства для передачи в форму
            self.recommended_medication = type('RecommendedMedication', (), {
                'name': medication_name
            })()
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['recommended_medication'] = self.recommended_medication
        return kwargs
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)
        messages.success(self.request, _('Лекарство успешно добавлено в план лечения'))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        context['owner'] = self.treatment_plan.owner
        context['owner_model'] = self.treatment_plan.owner._meta.model_name
        context['recommended_medication'] = self.recommended_medication
        context['title'] = _('Быстрое добавление лекарства')
        
        # Получаем пациента
        if hasattr(self.treatment_plan.owner, 'patient'):
            context['patient'] = self.treatment_plan.owner.patient
        elif hasattr(self.treatment_plan.owner, 'get_patient'):
            context['patient'] = self.treatment_plan.owner.get_patient()
        
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.treatment_plan.owner._meta.model_name,
                          'owner_id': self.treatment_plan.owner.id,
                          'pk': self.treatment_plan.pk
                      })


@csrf_exempt
def medication_info_view(request, medication_id):
    """
    AJAX endpoint для получения информации о лекарстве
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    # Получаем ID пациента из параметров
    patient_id = request.GET.get('patient_id')
    patient = None
    
    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            pass
    
    # Получаем ID торгового наименования из параметров
    trade_name_id = request.GET.get('trade_name_id')
    
    # Получаем информацию о лекарстве
    medication_info = TreatmentMedicationService.get_medication_info(medication_id, patient, trade_name_id)
    
    if medication_info:
        return JsonResponse({
            'success': True,
            'medication': medication_info
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Medication not found'
        })
