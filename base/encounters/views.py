from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from .models import Encounter, EncounterDiagnosis, TreatmentLabTest
from .forms import (
    EncounterForm, EncounterUpdateForm, EncounterDiagnosisForm,
    EncounterDiagnosisAdvancedForm, TreatmentLabTestForm
)
from patients.models import Patient
from treatment_management.models import TreatmentPlan


class EncounterListView(LoginRequiredMixin, ListView):
    """Представление для списка обращений"""
    model = Encounter
    template_name = 'encounters/list.html'
    context_object_name = 'encounters'
    paginate_by = 20

    def get_queryset(self):
        return Encounter.objects.select_related('patient', 'doctor').order_by('-date_start')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Обращения'
        return context


class EncounterDetailView(LoginRequiredMixin, DetailView):
    """Представление для детального просмотра обращения"""
    model = Encounter
    template_name = 'encounters/detail.html'
    context_object_name = 'encounter'

    def get_queryset(self):
        return Encounter.objects.select_related(
            'patient', 'doctor'
        ).prefetch_related(
            'diagnoses__diagnosis'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.object
        
        # Добавляем порядковый номер обращения для данного пациента
        patient_encounters = Encounter.objects.filter(
            patient=encounter.patient
        ).order_by('date_start')
        
        # Находим позицию текущего обращения в списке обращений пациента
        encounter_position = 1
        for i, patient_encounter in enumerate(patient_encounters):
            if patient_encounter.pk == encounter.pk:
                encounter_position = i + 1
                break
        
        context['encounter_number'] = encounter_position
        
        # Добавляем информацию о диагнозах
        main_diagnosis = encounter.diagnoses.filter(diagnosis_type='main').first()
        complications = encounter.diagnoses.filter(diagnosis_type='complication')
        comorbidities = encounter.diagnoses.filter(diagnosis_type='comorbidity')
        
        context.update({
            'main_diagnosis': main_diagnosis,
            'complications': complications,
            'comorbidities': comorbidities,
            'patient': encounter.patient,
        })
        
        # Добавляем информацию о планах лечения
        from treatment_management.models import TreatmentPlan
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(encounter)
        treatment_plans = TreatmentPlan.objects.filter(
            content_type=content_type,
            object_id=encounter.id
        )
        context['treatment_plans'] = treatment_plans
        
        # Добавляем информацию о планах обследования
        try:
            from examination_management.models import ExaminationPlan
            examination_plans = ExaminationPlan.objects.filter(encounter=encounter)
            
            # Если планов обследования нет, автоматически создаем "Основной" план
            if not examination_plans.exists():
                ExaminationPlan.objects.create(
                    encounter=encounter,
                    name='Основной',
                    description='Автоматически созданный основной план обследования'
                )
                # Обновляем queryset после создания
                examination_plans = ExaminationPlan.objects.filter(encounter=encounter)
            
            context['examination_plans'] = examination_plans
        except ImportError:
            # Если приложение examination_management не установлено
            context['examination_plans'] = []
        
        # Добавляем прикрепленные документы
        context['documents'] = encounter.documents.all()
        
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


class EncounterDiagnosisAdvancedView(UpdateView):
    """Представление для расширенной установки диагнозов"""
    model = Encounter
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_advanced_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Установить диагнозы'
        context['patient'] = self.object.patient
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Диагнозы успешно установлены')
        return response

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDiagnosisAdvancedCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания расширенного диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_advanced_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        context['encounter'] = encounter
        context['patient'] = encounter.patient
        context['title'] = 'Добавить диагноз'
        return context

    def form_valid(self, form):
        encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        form.instance.encounter = encounter
        messages.success(self.request, 'Диагноз успешно добавлен')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.kwargs['encounter_pk']})


class EncounterDiagnosisAdvancedUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования расширенного диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_advanced_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['title'] = 'Редактировать диагноз'
        return context

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.encounter.pk})


class EncounterDiagnosisAdvancedDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления расширенного диагноза"""
    model = EncounterDiagnosis
    template_name = 'encounters/diagnosis_advanced_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['title'] = 'Удалить диагноз'
        return context

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.encounter.pk})


class TreatmentPlansView(LoginRequiredMixin, ListView):
    """Представление для списка планов лечения"""
    model = TreatmentPlan
    template_name = 'encounters/treatment_plans.html'
    context_object_name = 'treatment_plans'

    def get_queryset(self):
        encounter_pk = self.kwargs.get('encounter_pk')
        content_type = ContentType.objects.get_for_model(Encounter)
        return TreatmentPlan.objects.filter(
            content_type=content_type,
            object_id=encounter_pk
        ).prefetch_related('medications', 'lab_tests')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter_pk = self.kwargs.get('encounter_pk')
        context['encounter'] = get_object_or_404(Encounter, pk=encounter_pk)
        context['patient'] = context['encounter'].patient
        context['title'] = 'Планы лечения'
        return context


class TreatmentLabTestCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания лабораторного назначения"""
    
    model = TreatmentLabTest
    form_class = TreatmentLabTestForm
    template_name = 'encounters/treatment_lab_test_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        context['treatment_plan'] = treatment_plan
        context['encounter'] = treatment_plan.encounter
        context['patient'] = treatment_plan.encounter.patient
        context['title'] = 'Добавить лабораторное исследование'
        context['next_url'] = self.request.GET.get('next', reverse('encounters:treatment_plans', kwargs={'encounter_pk': treatment_plan.encounter.pk}))
        return context
    
    def form_valid(self, form):
        treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        form.instance.treatment_plan = treatment_plan
        messages.success(self.request, 'Лабораторное исследование успешно добавлено в план лечения.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.treatment_plan.encounter.pk}))


class TreatmentLabTestUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования лабораторного назначения"""
    
    model = TreatmentLabTest
    form_class = TreatmentLabTestForm
    template_name = 'encounters/treatment_lab_test_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['encounter'] = self.object.treatment_plan.encounter
        context['patient'] = self.object.treatment_plan.encounter.patient
        context['title'] = 'Редактировать лабораторное исследование'
        context['next_url'] = self.request.GET.get('next', reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.treatment_plan.encounter.pk}))
        return context
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.treatment_plan.encounter.pk}))


class TreatmentLabTestDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления лабораторного назначения"""
    
    model = TreatmentLabTest
    template_name = 'encounters/treatment_lab_test_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['encounter'] = self.object.treatment_plan.encounter
        context['patient'] = self.object.treatment_plan.encounter.patient
        context['title'] = 'Удалить лабораторное исследование'
        context['next_url'] = self.request.GET.get('next', reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.treatment_plan.encounter.pk}))
        return context
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.treatment_plan.encounter.pk}))


class EncounterCloseView(LoginRequiredMixin, View):
    """Представление для закрытия случая"""
    
    def post(self, request, pk):
        encounter = get_object_or_404(Encounter, pk=pk)
        if encounter.is_active:
            encounter.is_active = False
            encounter.date_end = timezone.now()
            encounter.save()
            messages.success(request, 'Случай успешно закрыт')
        return redirect('encounters:encounter_detail', pk=pk)


class EncounterReopenView(LoginRequiredMixin, View):
    """Представление для возврата случая в активное состояние"""
    
    def post(self, request, pk):
        encounter = get_object_or_404(Encounter, pk=pk)
        if not encounter.is_active:
            encounter.is_active = True
            encounter.date_end = None
            encounter.save()
            messages.success(request, 'Случай возвращен в активное состояние')
        return redirect('encounters:encounter_detail', pk=pk)


class EncounterDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления случая"""
    
    model = Encounter
    template_name = 'encounters/encounter_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('patients:patient_detail', kwargs={'pk': self.object.patient.pk}) 