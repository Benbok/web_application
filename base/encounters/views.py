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
    
    elif 'api/medication-info' in path:
        # AJAX endpoint для информации о лекарстве
        medication_id = kwargs.get('medication_id')
        return redirect('treatment_management:medication_info', medication_id=medication_id)
    
    # Если не удалось определить URL, перенаправляем на главную страницу
    return redirect('patients:home')

from .models import Encounter, EncounterDiagnosis, TreatmentPlan, TreatmentMedication
from .services.encounter_service import EncounterService
from .services import TreatmentPlanService
from patients.models import Patient
from .forms import (
    EncounterForm, EncounterCloseForm, EncounterUpdateForm, EncounterReopenForm, 
    EncounterUndoForm, EncounterDiagnosisForm, EncounterDiagnosisAdvancedForm,
    TreatmentPlanForm, TreatmentMedicationForm
)
from departments.models import Department, PatientDepartmentStatus
from pharmacy.services import RegimenService, PatientRecommendationService
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
        context['is_active'] = details['is_active']
        context['has_documents'] = details['has_documents']
        
        # Добавляем информацию о командах
        context['command_history'] = service.get_command_history()
        context['last_command'] = service.get_last_command()
        
        # Добавляем информацию о диагнозах (уже загружены через prefetch_related)
        context['main_diagnosis'] = encounter.get_main_diagnosis()
        context['complications'] = encounter.get_complications()
        context['comorbidities'] = encounter.get_comorbidities()
        context['treatment_plans'] = encounter.treatment_plans.all()
        
        return context

class EncounterCreateView(CreateView):
    model = Encounter
    form_class = EncounterForm
    template_name = 'encounters/form.html'

    def setup(self, request, *args, **kwargs):
        """Получаем пациента до основной логики."""
        super().setup(request, *args, **kwargs)
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])

    def form_valid(self, form):
        """Добавляем пациента и врача перед сохранением."""
        form.instance.patient = self.patient
        form.instance.doctor = self.request.user
        
        # Если дата начала не установлена, устанавливаем текущую дату и время
        if not form.instance.date_start:
            form.instance.date_start = timezone.now()
        
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавляем в контекст пациента и заголовок."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['title'] = 'Новое обращение'
        return context
    
    def get_success_url(self):
        """Редирект после успешного создания."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterUpdateView(UpdateView):
    model = Encounter
    form_class = EncounterUpdateForm
    template_name = 'encounters/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['title'] = 'Редактировать обращение'
        return context

    def form_valid(self, form):
        old_outcome = self.get_object().outcome
        old_transfer_to_department = self.get_object().transfer_to_department

        # Если исход пустой, очищаем дату завершения
        if not form.cleaned_data.get('outcome'):
            form.instance.date_end = None
        # Если исход установлен, но дата завершения пуста, заполняем ее текущим временем
        elif form.cleaned_data.get('outcome') and not form.cleaned_data.get('date_end'):
            form.instance.date_end = timezone.now()

        # НОВАЯ ЛОГИКА: Проверка наличия документов перед сохранением, если случай закрывается
        # Случай считается закрытым, если outcome установлен и date_end установлен
        if form.cleaned_data.get('outcome') and form.cleaned_data.get('date_end'):
            if not self.object.documents.exists():
                form.add_error(None, "Невозможно закрыть случай обращения: нет прикрепленных документов.")
                return self.form_invalid(form)

        response = super().form_valid(form)

        # Обработка перевода в отделение
        if form.cleaned_data.get('outcome') == 'transferred':
            new_transfer_to_department = form.cleaned_data.get('transfer_to_department')
            if new_transfer_to_department and (not old_transfer_to_department or old_transfer_to_department != new_transfer_to_department):
                # Создаем запись о переводе пациента в отделение
                PatientDepartmentStatus.objects.create(
                    patient=self.object.patient,
                    department=new_transfer_to_department,
                    status='admitted',
                    admission_date=timezone.now(),
                    source_encounter=self.object
                )
                messages.success(self.request, f"Пациент переведен в отделение «{new_transfer_to_department.name}».")

        messages.success(self.request, "Обращение успешно обновлено.")
        return response

    def get_success_url(self):
        """Редирект после успешного обновления."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterDiagnosisView(UpdateView):
    """Представление для установки диагноза в случае обращения"""
    model = Encounter
    form_class = EncounterDiagnosisForm
    template_name = 'encounters/diagnosis_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object
        context['patient'] = self.object.patient
        context['title'] = 'Установить диагноз'
        return context

    def form_valid(self, form):
        """Сохраняем диагноз и показываем сообщение об успехе."""
        response = super().form_valid(form)
        messages.success(self.request, f'Диагноз успешно установлен: {form.instance.diagnosis}')
        return response

    def get_success_url(self):
        """Редирект на детальную страницу случая."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterDiagnosisAdvancedView(DetailView):
    """Представление для работы с расширенной структурой диагнозов"""
    model = Encounter
    template_name = 'encounters/diagnosis_advanced.html'
    context_object_name = 'encounter'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['title'] = 'Управление диагнозами'
        context['main_diagnosis'] = self.object.get_main_diagnosis()
        context['complications'] = self.object.get_complications()
        context['comorbidities'] = self.object.get_comorbidities()
        return context

class EncounterDiagnosisCreateView(CreateView):
    """Представление для создания нового диагноза"""
    model = EncounterDiagnosis
    form_class = EncounterDiagnosisAdvancedForm
    template_name = 'encounters/diagnosis_create.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        encounter_pk = self.kwargs.get('encounter_pk')
        if encounter_pk:
            self.encounter = get_object_or_404(Encounter, pk=encounter_pk)
        else:
            self.encounter = None
    
    def form_valid(self, form):
        # Убеждаемся, что encounter установлен
        if not hasattr(self, 'encounter') or self.encounter is None:
            encounter_pk = self.kwargs.get('encounter_pk')
            if encounter_pk:
                self.encounter = get_object_or_404(Encounter, pk=encounter_pk)
            else:
                raise ValueError("encounter_pk не найден в kwargs")
        
        form.instance.encounter = self.encounter
        response = super().form_valid(form)
        messages.success(self.request, f'Диагноз успешно добавлен: {form.instance.get_display_name()}')
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['title'] = 'Редактировать диагноз'
        return context
    
    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.object.encounter.pk})

class EncounterDiagnosisDeleteView(DeleteView):
    """Представление для удаления диагноза"""
    model = EncounterDiagnosis
    template_name = 'encounters/diagnosis_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('encounters:encounter_diagnosis_advanced', kwargs={'pk': self.object.encounter.pk})

class TreatmentPlanListView(ListView):
    """Представление для списка планов лечения"""
    model = TreatmentPlan
    template_name = 'encounters/treatment_plans.html'
    context_object_name = 'treatment_plans'
    
    def get_queryset(self):
        self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        return self.encounter.treatment_plans.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.encounter
        context['patient'] = self.encounter.patient
        context['title'] = 'Планы лечения'
        
        # Добавляем рекомендации по лекарствам
        recommendations = TreatmentPlanService.get_medication_recommendations(self.encounter)
        context['recommendations'] = recommendations
        
        return context

class TreatmentPlanCreateView(CreateView):
    """Представление для создания плана лечения"""
    model = TreatmentPlan
    form_class = TreatmentPlanForm
    template_name = 'encounters/treatment_plan_form.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
    
    def form_valid(self, form):
        # Создаем план лечения без автоматического добавления препаратов
        form.instance.encounter = self.encounter
        treatment_plan = form.save()
        
        messages.success(self.request, f'План лечения успешно создан: {treatment_plan.name}')
        
        # Перенаправляем на детальный просмотр созданного плана
        return redirect('encounters:treatment_plan_detail', pk=treatment_plan.pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.encounter
        context['patient'] = self.encounter.patient
        context['title'] = 'Создать план лечения'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.object.pk})

class TreatmentPlanDetailView(DetailView):
    """Представление для детального просмотра плана лечения"""
    model = TreatmentPlan
    template_name = 'encounters/treatment_plan_detail.html'
    context_object_name = 'treatment_plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['title'] = f'План лечения: {self.object.name}'
        context['medications'] = self.object.medications.all()
        return context


class TreatmentPlanDeleteView(DeleteView):
    """Представление для удаления плана лечения"""
    model = TreatmentPlan
    template_name = 'encounters/treatment_plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        context['medications'] = self.object.medications.all()
        context['title'] = 'Удалить план лечения'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plans', kwargs={'encounter_pk': self.object.encounter.pk})


class TreatmentMedicationCreateView(CreateView):
    """Представление для добавления лекарства в план лечения"""
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'encounters/treatment_medication_form.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['treatment_plan_pk'])
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)
        messages.success(self.request, f'Лекарство успешно добавлено в план лечения')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        context['encounter'] = self.treatment_plan.encounter
        context['patient'] = self.treatment_plan.encounter.patient
        context['title'] = 'Добавить лекарство'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.treatment_plan.pk})


@method_decorator(csrf_exempt, name='dispatch')
class MedicationInfoView(View):
    """AJAX endpoint для получения информации о препарате"""
    
    def get(self, request, medication_id):
        try:
            from pharmacy.models import Medication
            medication = Medication.objects.get(pk=medication_id)
            
            # Получаем информацию о пациенте из параметров запроса
            patient_id = request.GET.get('patient_id')
            patient = None
            if patient_id:
                from patients.models import Patient
                try:
                    patient = Patient.objects.get(pk=patient_id)
                except Patient.DoesNotExist:
                    pass
            
            # Получаем информацию о препарате
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
            
            # Получаем торговые названия
            trade_names = medication.trade_names.all()
            if trade_names.exists():
                medication_info['trade_names'] = [
                    {
                        'name': tn.name,
                        'group': tn.medication_group.name if tn.medication_group else None,
                        'release_form': tn.release_form.name if tn.release_form else None,
                    }
                    for tn in trade_names
                ]
            
            # Получаем стандартные дозировки из pharmacy app с учетом пациента
            from pharmacy.models import Regimen, DosingInstruction, PopulationCriteria
            from datetime import date
            
            if patient and patient.birth_date:
                # Вычисляем возраст пациента в днях
                age_days = (date.today() - patient.birth_date).days
                
                # Ищем схемы с подходящими возрастными критериями
                suitable_regimens = []
                
                regimens_with_instructions = Regimen.objects.filter(
                    medication=medication,
                    dosing_instructions__isnull=False
                ).distinct()
                
                for regimen in regimens_with_instructions:
                    # Проверяем критерии населения для этой схемы
                    population_criteria = PopulationCriteria.objects.filter(regimen=regimen)
                    
                    if not population_criteria.exists():
                        # Если нет критериев, считаем подходящим
                        suitable_regimens.append(regimen)
                        continue
                    
                    for criteria in population_criteria:
                        # Проверяем возрастные критерии
                        age_suitable = True
                        if criteria.min_age_days and age_days < criteria.min_age_days:
                            age_suitable = False
                        if criteria.max_age_days and age_days > criteria.max_age_days:
                            age_suitable = False
                        
                        # Проверяем весовые критерии (если есть)
                        weight_suitable = True
                        patient_weight = getattr(patient, 'weight', None)
                        if patient_weight and criteria.min_weight_kg and patient_weight < criteria.min_weight_kg:
                            weight_suitable = False
                        if patient_weight and criteria.max_weight_kg and patient_weight > criteria.max_weight_kg:
                            weight_suitable = False
                        
                        if age_suitable and weight_suitable:
                            suitable_regimens.append(regimen)
                            break
                
                # Если нашли подходящие схемы, берем первую
                if suitable_regimens:
                    regimen = suitable_regimens[0]
                else:
                    # Если не нашли подходящих, берем первую доступную
                    regimen = regimens_with_instructions.first()
            else:
                # Если нет информации о пациенте, берем первую схему
                regimens_with_instructions = Regimen.objects.filter(
                    medication=medication,
                    dosing_instructions__isnull=False
                ).distinct()
                regimen = regimens_with_instructions.first() if regimens_with_instructions.exists() else None
            
            if regimen:
                dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
                if dosing_instruction:
                    medication_info['dosage'] = dosing_instruction.dose_description
                    medication_info['frequency'] = dosing_instruction.frequency_description
                    medication_info['route'] = dosing_instruction.route.name if dosing_instruction.route else 'oral'
                    medication_info['duration'] = dosing_instruction.duration_description
                    medication_info['instructions'] = regimen.notes or ''
                    
                    # Добавляем информацию о выбранной схеме
                    medication_info['selected_regimen'] = {
                        'name': regimen.name,
                        'notes': regimen.notes or ''
                    }
            
            return JsonResponse({
                'success': True,
                'medication': medication_info
            })
            
        except Medication.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Препарат не найден'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class TreatmentMedicationUpdateView(UpdateView):
    """Представление для редактирования лекарства в плане лечения"""
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'encounters/treatment_medication_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['encounter'] = self.object.treatment_plan.encounter
        context['patient'] = self.object.treatment_plan.encounter.patient
        context['title'] = 'Редактировать лекарство'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.object.treatment_plan.pk})

class TreatmentMedicationDeleteView(DeleteView):
    """Представление для удаления лекарства из плана лечения"""
    model = TreatmentMedication
    template_name = 'encounters/treatment_medication_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['encounter'] = self.object.treatment_plan.encounter
        context['patient'] = self.object.treatment_plan.encounter.patient
        context['title'] = 'Удалить лекарство'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.object.treatment_plan.pk})

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


@method_decorator(csrf_exempt, name='dispatch')
class TreatmentRegimensView(View):
    """
    AJAX view для получения схем лечения по диагнозу.
    Возвращает JSON с рекомендациями по препаратам.
    """
    
    def get(self, request, *args, **kwargs):
        diagnosis_id = request.GET.get('diagnosis_id')
        encounter_id = request.GET.get('encounter_id')
        
        if not diagnosis_id:
            return JsonResponse({'error': 'Не указан ID диагноза'}, status=400)
        
        try:
            diagnosis = Diagnosis.objects.get(id=diagnosis_id)
        except Diagnosis.DoesNotExist:
            return JsonResponse({'error': 'Диагноз не найден'}, status=404)
        
        # Получаем схемы лечения по диагнозу
        regimens = RegimenService.get_regimens_by_diagnosis(diagnosis.id)
        
        # Если указан encounter_id, получаем персонализированные рекомендации
        personalized_recommendations = None
        if encounter_id:
            try:
                encounter = Encounter.objects.get(id=encounter_id)
                personalized_recommendations = PatientRecommendationService.get_patient_recommendations(
                    patient=encounter.patient,
                    diagnosis=diagnosis
                )
            except Encounter.DoesNotExist:
                pass
        
        return JsonResponse({
            'diagnosis': {
                'id': diagnosis.id,
                'name': diagnosis.name,
                'code': diagnosis.code
            },
            'regimens': regimens,
            'personalized_recommendations': personalized_recommendations
        })


@method_decorator(csrf_exempt, name='dispatch')
class PatientRecommendationsView(View):
    """
    AJAX view для получения персонализированных рекомендаций для пациента.
    """
    
    def get(self, request, *args, **kwargs):
        encounter_id = request.GET.get('encounter_id')
        diagnosis_id = request.GET.get('diagnosis_id')
        
        if not encounter_id:
            return JsonResponse({'error': 'Не указан ID обращения'}, status=400)
        
        try:
            encounter = Encounter.objects.get(id=encounter_id)
        except Encounter.DoesNotExist:
            return JsonResponse({'error': 'Обращение не найдено'}, status=404)
        
        diagnosis = None
        if diagnosis_id:
            try:
                diagnosis = Diagnosis.objects.get(id=diagnosis_id)
            except Diagnosis.DoesNotExist:
                pass
        
        recommendations = PatientRecommendationService.get_patient_recommendations(
            patient=encounter.patient,
            diagnosis=diagnosis
        )
        
        return JsonResponse({
            'patient': {
                'id': encounter.patient.id,
                'name': encounter.patient.full_name,
                'age_days': (timezone.now().date() - encounter.patient.birth_date).days
            },
            'recommendations': recommendations
        })


class QuickAddMedicationView(CreateView):
    """Представление для быстрого добавления препарата из рекомендаций"""
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'encounters/quick_add_medication.html'
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs.get('plan_pk'))
        self.encounter = self.treatment_plan.encounter
        self.patient = self.encounter.patient
        
        # Получаем данные о препарате из рекомендации
        medication_id = self.kwargs.get('medication_id')
        if medication_id:
            from pharmacy.models import Medication
            try:
                self.recommended_medication = Medication.objects.get(pk=medication_id)
            except Medication.DoesNotExist:
                self.recommended_medication = None
                messages.warning(request, f"Препарат с ID {medication_id} не найден в справочнике")
        else:
            self.recommended_medication = None
    
    def get_initial(self):
        """Устанавливаем начальные значения из рекомендации"""
        initial = super().get_initial()
        if self.recommended_medication:
            initial['medication'] = self.recommended_medication
            # Можно добавить другие поля из рекомендации, если они есть
        else:
            # Если препарат не найден в базе, но есть название из рекомендации
            medication_name = self.kwargs.get('medication_name')
            if medication_name:
                initial['custom_medication'] = medication_name
        return initial
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        
        # Если препарат выбран из рекомендации, можно добавить дополнительные данные
        if form.cleaned_data.get('medication') and self.recommended_medication:
            # Здесь можно добавить логику для автоматического заполнения полей
            # на основе данных из рекомендации
            pass
        
        response = super().form_valid(form)
        messages.success(self.request, f'Препарат "{form.instance.get_medication_name()}" успешно добавлен в план лечения')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        context['encounter'] = self.encounter
        context['patient'] = self.patient
        context['recommended_medication'] = self.recommended_medication
        context['title'] = 'Быстрое добавление препарата'
        return context
    
    def get_success_url(self):
        return reverse('encounters:treatment_plan_detail', kwargs={'pk': self.treatment_plan.pk})