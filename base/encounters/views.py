from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from .models import Encounter, EncounterDiagnosis
from .forms import (
    EncounterForm, EncounterUpdateForm, EncounterDiagnosisForm,
    EncounterDiagnosisAdvancedForm, EncounterCloseForm
)
from patients.models import Patient



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
        try:
            from treatment_management.models import TreatmentPlan
            treatment_plans = TreatmentPlan.objects.filter(encounter=encounter)
            context['treatment_plans'] = treatment_plans
        except ImportError:
            # Если приложение treatment_management не установлено
            context['treatment_plans'] = []
        
        # Добавляем информацию о планах обследования
        try:
            from examination_management.models import ExaminationPlan
            examination_plans = ExaminationPlan.objects.filter(encounter=encounter)
            context['examination_plans'] = examination_plans
        except ImportError:
            # Если приложение examination_management не установлено
            context['examination_plans'] = []
        
        # Добавляем прикрепленные документы (включая дневники)
        try:
            from documents.models import ClinicalDocument
            # Получаем все документы, связанные с этим случаем
            # Используем прямое поле encounter в ClinicalDocument
            all_documents = ClinicalDocument.objects.filter(
                encounter=encounter
            ).select_related('document_type', 'author').order_by('-datetime_document')
            
            # Убираем GenericRelation, используем только прямую связь
            # generic_documents = encounter.documents.all()
            
            # Объединяем документы, убирая дубликаты
            all_document_ids = set()
            combined_documents = []
            
            # Добавляем документы из новой системы
            for doc in all_documents:
                combined_documents.append(doc)
                all_document_ids.add(doc.pk)
            
            # Убираем GenericRelation, так как используем только прямую связь
            # for doc in generic_documents:
            #     if doc.pk not in all_document_ids:
            #         combined_documents.append(doc)
            #         all_document_ids.add(doc.pk)
            
            context['documents'] = combined_documents
        except ImportError:
            # Fallback к прямой связи, если приложение documents не установлено
            context['documents'] = encounter.clinical_documents.all()
        
        return context


class EncounterCreateView(LoginRequiredMixin, CreateView):
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
        
        # Показываем Toastr-уведомление
        from django.contrib import messages
        messages.success(self.request, f'Обращение для пациента {self.patient.get_full_name_with_age()} успешно создано')
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['title'] = 'Создать обращение'
        return context
    
    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterUpdateView(LoginRequiredMixin, UpdateView):
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
        
        # Показываем Toastr-уведомление
        from django.contrib import messages
        messages.success(self.request, f'Обращение №{self.object.pk} успешно обновлено')
        
        return response

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDiagnosisView(LoginRequiredMixin, UpdateView):
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
        
        # Показываем Toastr-уведомление
        from django.contrib import messages
        messages.success(self.request, f'Диагноз для обращения №{self.object.pk} успешно установлен')
        
        return response

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDiagnosisAdvancedView(LoginRequiredMixin, UpdateView):
    """Представление для расширенной установки диагнозов"""
    model = Encounter
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.object
        
        # Добавляем информацию о диагнозах
        main_diagnosis = encounter.diagnoses.filter(diagnosis_type='main').first()
        complications = encounter.diagnoses.filter(diagnosis_type='complication')
        comorbidities = encounter.diagnoses.filter(diagnosis_type='comorbidity')
        
        context.update({
            'title': 'Установить диагнозы',
            'patient': encounter.patient,
            'encounter': encounter,
            'main_diagnosis': main_diagnosis,
            'complications': complications,
            'comorbidities': comorbidities,
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Показываем Toastr-уведомление
        from django.contrib import messages
        messages.success(self.request, f'Диагнозы для обращения №{self.object.pk} успешно установлены')
        
        return response

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDiagnosisAdvancedCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания расширенного диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        
        # Добавляем информацию о диагнозах
        main_diagnosis = encounter.diagnoses.filter(diagnosis_type='main').first()
        complications = encounter.diagnoses.filter(diagnosis_type='complication')
        comorbidities = encounter.diagnoses.filter(diagnosis_type='comorbidity')
        
        context.update({
            'encounter': encounter,
            'patient': encounter.patient,
            'title': 'Добавить диагноз',
            'main_diagnosis': main_diagnosis,
            'complications': complications,
            'comorbidities': comorbidities,
        })
        return context

    def get_form_kwargs(self):
        """Передаем encounter в форму, чтобы скрытое поле и queryset были корректными."""
        kwargs = super().get_form_kwargs()
        encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        kwargs['encounter'] = encounter
        return kwargs

    def form_valid(self, form):
        encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        form.instance.encounter = encounter
        
        # Показываем Toastr-уведомление
        from django.contrib import messages
        messages.success(self.request, f'Диагноз для обращения №{encounter.pk} успешно добавлен')
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.kwargs['encounter_pk']})


class EncounterDiagnosisAdvancedUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования расширенного диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.object.encounter
        
        # Добавляем информацию о диагнозах
        main_diagnosis = encounter.diagnoses.filter(diagnosis_type='main').first()
        complications = encounter.diagnoses.filter(diagnosis_type='complication')
        comorbidities = encounter.diagnoses.filter(diagnosis_type='comorbidity')
        
        context.update({
            'encounter': encounter,
            'patient': encounter.patient,
            'title': 'Редактировать диагноз',
            'main_diagnosis': main_diagnosis,
            'complications': complications,
            'comorbidities': comorbidities,
        })
        return context

    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.object.encounter.pk})

    def get_form_kwargs(self):
        """Передаем encounter в форму для корректного hidden-поля."""
        kwargs = super().get_form_kwargs()
        kwargs['encounter'] = self.object.encounter
        return kwargs


class EncounterDiagnosisAdvancedDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления расширенного диагноза"""
    model = EncounterDiagnosis
    template_name = 'encounters/diagnosis_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.object.encounter
        
        # Добавляем информацию о диагнозах
        main_diagnosis = encounter.diagnoses.filter(diagnosis_type='main').first()
        complications = encounter.diagnoses.filter(diagnosis_type='complication')
        comorbidities = encounter.diagnoses.filter(diagnosis_type='comorbidity')
        
        context.update({
            'encounter': encounter,
            'patient': encounter.patient,
            'title': 'Удалить диагноз',
            'main_diagnosis': main_diagnosis,
            'complications': complications,
            'comorbidities': comorbidities,
        })
        return context

    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.object.encounter.pk})


class EncounterCloseView(LoginRequiredMixin, View):
    """Представление для закрытия случая"""
    
    def get(self, request, pk):
        """Показывает форму для закрытия случая"""
        encounter = get_object_or_404(Encounter, pk=pk)
        if not encounter.is_active:
            # Показываем Toastr-уведомление
            from django.contrib import messages
            messages.warning(request, 'Этот случай обращения уже находится в закрытом состоянии')
            return redirect('encounters:encounter_detail', pk=pk)
        
        # Вычисляем порядковый номер обращения для данного пациента
        patient_encounters = Encounter.objects.filter(
            patient=encounter.patient
        ).order_by('date_start')
        
        # Находим позицию текущего обращения в списке обращений пациента
        encounter_position = 1
        for i, patient_encounter in enumerate(patient_encounters):
            if patient_encounter.pk == encounter.pk:
                encounter_position = i + 1
                break
        
        form = EncounterCloseForm(instance=encounter)
        return render(request, 'encounters/close_form.html', {
            'form': form,
            'encounter': encounter,
            'encounter_number': encounter_position,
            'title': 'Закрыть случай'
        })
    
    def post(self, request, pk):
        """Обрабатывает закрытие случая"""
        encounter = get_object_or_404(Encounter, pk=pk)
        if not encounter.is_active:
            # Показываем Toastr-уведомление
            from django.contrib import messages
            messages.warning(request, 'Этот случай обращения уже находится в закрытом состоянии')
            return redirect('encounters:encounter_detail', pk=pk)
        
        form = EncounterCloseForm(request.POST, instance=encounter)
        if form.is_valid():
            try:
                # Сохраняем через форму, которая использует правильную логику
                form.save(commit=True, user=request.user)
                
                # Показываем Toastr-уведомление
                from django.contrib import messages
                messages.success(request, f"Случай обращения для пациента {encounter.patient.get_full_name_with_age()} успешно закрыт.")
                
                return redirect('encounters:encounter_detail', pk=pk)
            except Exception as e:
                # Показываем Toastr-уведомление
                from django.contrib import messages
                messages.error(request, f"Не удалось закрыть случай обращения: {str(e)}")
        else:
            # Показываем Toastr-уведомление
            from django.contrib import messages
            messages.error(request, "Пожалуйста, исправьте ошибки в форме закрытия случая")
        
        return render(request, 'encounters/close_form.html', {
            'form': form,
            'encounter': encounter,
            'title': 'Закрыть случай'
        })


class EncounterReopenView(LoginRequiredMixin, View):
    """Представление для возврата случая в активное состояние"""
    
    def post(self, request, pk):
        encounter = get_object_or_404(Encounter, pk=pk)
        if encounter.is_active:
            # Показываем Toastr-уведомление
            from django.contrib import messages
            messages.warning(request, 'Этот случай обращения уже находится в активном состоянии')
            return redirect('encounters:encounter_detail', pk=pk)
        
        try:
            # Используем сервис для правильной логики возврата
            from .services.encounter_service import EncounterService
            service = EncounterService(encounter)
            
            if service.reopen_encounter(user=request.user):
                # Показываем Toastr-уведомление
                from django.contrib import messages
                messages.success(request, f"Случай обращения для пациента {encounter.patient.get_full_name_with_age()} возвращен в активное состояние.")
            else:
                # Показываем Toastr-уведомление
                from django.contrib import messages
                messages.error(request, f"Не удалось вернуть случай обращения для пациента {encounter.patient.get_full_name_with_age()}.")
                
        except Exception as e:
            # Показываем Toastr-уведомление
            from django.contrib import messages
            messages.error(request, f"Ошибка при возврате случая обращения: {str(e)}")
        
        return redirect('encounters:encounter_detail', pk=pk)


class EncounterDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления случая"""
    
    model = Encounter
    template_name = 'encounters/encounter_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('patients:patient_detail', kwargs={'pk': self.object.patient.pk}) 