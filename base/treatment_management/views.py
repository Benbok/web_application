from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, View
)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError

from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation
from .forms import TreatmentPlanForm, TreatmentMedicationForm, TreatmentMedicationWithScheduleForm, QuickAddMedicationForm, TreatmentRecommendationForm
from .services import (
    TreatmentPlanService, TreatmentMedicationService, TreatmentRecommendationService
)
from patients.models import Patient
from clinical_scheduling.mixins import MedicationScheduleRedirectMixin

# Общая функция для преобразования текстового способа введения в ID AdministrationMethod
def map_route_to_form_value(route_text):
    """
    Преобразует текстовое описание способа введения в ID AdministrationMethod.
    Теперь возвращает ID для ForeignKey поля route.
    """
    if not route_text:
        return None
    
    try:
        from pharmacy.models import AdministrationMethod
        # Ищем метод введения по точному названию
        method = AdministrationMethod.objects.filter(name__iexact=route_text).first()
        if method:
            return method.id
        else:
            # Если не нашли точное совпадение, ищем по частичному совпадению
            method = AdministrationMethod.objects.filter(name__icontains=route_text).first()
            if method:
                return method.id
            else:
                # Если ничего не нашли, возвращаем None
                return None
    except Exception as e:
        print(f"Ошибка при поиске AdministrationMethod для '{route_text}': {e}")
        return None


class OwnerContextMixin:
    """
    Миксин для получения контекста владельца и пациента
    Устраняет дублирование кода в различных view классах
    """
    
    def get_owner(self):
        """
        Получает объект-владелец из URL параметров
        
        Returns:
            Объект-владелец (encounter, department_stay, etc.)
        """
        owner_model = self.kwargs.get('owner_model')
        owner_id = self.kwargs.get('owner_id')
        
        if not owner_model or not owner_id:
            raise ValueError("owner_model и owner_id должны быть указаны в URL")
        
        # Получаем ContentType для модели владельца
        content_type = ContentType.objects.get(model=owner_model)
        owner_class = content_type.model_class()
        owner = get_object_or_404(owner_class, id=owner_id)
        
        return owner
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        
        Args:
            owner: Объект-владелец
            
        Returns:
            Patient или None
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None
    
    def resolve_owner_from_plan(self, plan):
        """Возвращает владельца плана лечения с учетом гибридной архитектуры.
        Сначала использует прямые связи, затем GenericForeignKey.
        """
        if getattr(plan, 'patient_department_status_id', None):
            return plan.patient_department_status
        if getattr(plan, 'encounter_id', None):
            return plan.encounter
        return getattr(plan, 'owner', None)
    
    def setup_owner_context(self):
        """
        Настраивает контекст владельца и пациента
        Должен вызываться в dispatch() или get_context_data()
        """
        if not hasattr(self, 'owner'):
            self.owner = self.get_owner()
        
        if not hasattr(self, 'patient'):
            self.patient = self.get_patient_from_owner(self.owner)


class TreatmentPlanListView(LoginRequiredMixin, OwnerContextMixin, ListView):
    """
    Список планов лечения для указанного владельца
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_list.html'
    context_object_name = 'treatment_plans'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            from encounters.models import Encounter
            self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            self.owner = self.encounter
            self.owner_model = 'encounter'
            self.patient = self.encounter.patient
        else:
            # Используем универсальный подход с OwnerContextMixin
            self.setup_owner_context()
        return super().dispatch(request, *args, **kwargs)
    
    def setup_owner_context(self):
        """
        Настраивает контекст владельца и пациента для универсальных URL
        """
        owner_model = self.kwargs.get('owner_model')
        owner_id = self.kwargs.get('owner_id')
        
        if not owner_model or not owner_id:
            raise ValueError("owner_model и owner_id должны быть указаны в URL")
        
        # Получаем ContentType для модели владельца
        content_type = ContentType.objects.get(model=owner_model)
        owner_class = content_type.model_class()
        self.owner = get_object_or_404(owner_class, id=owner_id)
        self.owner_model = owner_model
        self.patient = self.get_patient_from_owner(self.owner)
    
    def get_queryset(self):
        # Используем сервис для получения планов
        return TreatmentPlanService.get_treatment_plans(self.owner)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
        context['patient'] = self.patient
        
        # Получаем рекомендации по лечению (если есть диагноз)
        if hasattr(self.owner, 'get_main_diagnosis_for_recommendations'):
            main_diagnosis = self.owner.get_main_diagnosis_for_recommendations()
            if main_diagnosis and self.patient:
                recommendations = TreatmentRecommendationService.get_medication_recommendations(
                    main_diagnosis.code, self.patient
                )
                context['recommendations'] = recommendations
        
        return context


class TreatmentPlanCreateView(LoginRequiredMixin, OwnerContextMixin, CreateView):
    """
    Создание нового плана лечения
    """
    model = TreatmentPlan
    form_class = TreatmentPlanForm
    template_name = 'treatment_management/plan_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Настраиваем контекст владельца
        self.setup_owner_context()
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Создаем план лечения через сервис
        treatment_plan = TreatmentPlanService.create_treatment_plan(
            owner=self.owner,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
            created_by=self.request.user
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
        
        # Устанавливаем initial значения для owner_type и owner_id
        if hasattr(self.owner, 'patient'):  # PatientDepartmentStatus
            kwargs['owner_type'] = 'department'
            kwargs['owner_id'] = self.owner.pk
        elif hasattr(self.owner, 'patient_id'):  # Encounter
            kwargs['owner_type'] = 'encounter'
            kwargs['owner_id'] = self.owner.pk
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
        context['title'] = _('Создать план лечения')
        return context


class TreatmentPlanDetailView(LoginRequiredMixin, OwnerContextMixin, DetailView):
    """
    Детальный просмотр плана лечения
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_detail.html'
    context_object_name = 'treatment_plan'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            from encounters.models import Encounter
            self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            self.owner = self.encounter
            self.owner_model = 'encounter'
            self.patient = self.encounter.patient
        else:
            # Используем универсальный подход с OwnerContextMixin
            self.setup_owner_context()
        return super().dispatch(request, *args, **kwargs)
    
    def setup_owner_context(self):
        """
        Настраивает контекст владельца и пациента для универсальных URL
        """
        owner_model = self.kwargs.get('owner_model')
        owner_id = self.kwargs.get('owner_id')
        
        if not owner_model or not owner_id:
            raise ValueError("owner_model и owner_id должны быть указаны в URL")
        
        # Получаем ContentType для модели владельца
        content_type = ContentType.objects.get(model=owner_model)
        owner_class = content_type.model_class()
        self.owner = get_object_or_404(owner_class, id=owner_id)
        self.owner_model = owner_model
        self.patient = self.get_patient_from_owner(self.owner)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner_model
        context['medications'] = self.object.medications.all()
        context['recommendations'] = self.object.recommendations.all()
        context['patient'] = self.patient
        
        return context


class TreatmentPlanUpdateView(LoginRequiredMixin, OwnerContextMixin, UpdateView):
    """
    Редактирование плана лечения
    """
    model = TreatmentPlan
    form_class = TreatmentPlanForm
    template_name = 'treatment_management/plan_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner = self.resolve_owner_from_plan(self.object)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['title'] = _('Редактировать план лечения')
        
        # Получаем пациента через миксин
        context['patient'] = self.get_patient_from_owner(owner) if owner is not None else None
        
        return context
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.object)
        return reverse('treatment_management:plan_detail',
                       kwargs={
                           'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                           'owner_id': owner.id if owner is not None else 0,
                           'pk': self.object.pk
                       })


class TreatmentPlanDeleteView(LoginRequiredMixin, OwnerContextMixin, DeleteView):
    """
    Удаление плана лечения (мягкое удаление)
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner = self.resolve_owner_from_plan(self.object)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['medications'] = self.object.medications.all()
        context['title'] = _('Отменить план лечения')
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Переопределяем метод delete для использования soft delete
        """
        self.object = self.get_object()
        
        # Сначала отменяем все активные назначения в плане
        for medication in self.object.medications.filter(status='active'):
            medication.cancel(
                reason="План лечения отменен",
                cancelled_by=request.user
            )
        
        # Отменяем все активные рекомендации в плане
        for recommendation in self.object.recommendations.filter(status='active'):
            recommendation.cancel(
                reason="План лечения отменен",
                cancelled_by=request.user
            )
        
        # Отменяем сам план лечения
        self.object.cancel(
            reason="Отменено через веб-интерфейс",
            cancelled_by=request.user
        )
        
        messages.success(request, _('План лечения и все назначения успешно отменены'))
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.object)
        return reverse('treatment_management:plan_list',
                       kwargs={
                           'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                           'owner_id': owner.id if owner is not None else 0
                       })


class TreatmentMedicationCreateView(LoginRequiredMixin, OwnerContextMixin, CreateView):
    """
    Добавление лекарства в план лечения с настройкой расписания
    """
    model = TreatmentMedication
    form_class = TreatmentMedicationWithScheduleForm
    template_name = 'treatment_management/medication_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)  # Сохраняем TreatmentMedication
        
        # Создаем расписание, если оно включено
        if form.cleaned_data.get('enable_schedule'):
            try:
                from clinical_scheduling.services import ClinicalSchedulingService
                ClinicalSchedulingService.create_schedule_for_assignment(
                    assignment=form.instance,
                    user=self.request.user,
                    start_date=form.cleaned_data['start_date'],
                    first_time=form.cleaned_data['first_time'],
                    times_per_day=form.cleaned_data['times_per_day'],
                    duration_days=form.cleaned_data['duration_days']
                )
                messages.success(self.request, _('Лекарство и расписание успешно созданы.'))
            except Exception as e:
                messages.warning(self.request, _('Лекарство создано, но возникла ошибка при создании расписания: {}').format(str(e)))
        else:
            messages.success(self.request, _('Лекарство успешно добавлено в план лечения.'))
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        owner = self.resolve_owner_from_plan(self.treatment_plan)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['title'] = _('Добавить лекарство')
        
        # Получаем пациента через миксин
        context['patient'] = self.get_patient_from_owner(owner) if owner is not None else None
        
        return context
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.treatment_plan)
        return reverse('treatment_management:plan_detail',
                       kwargs={
                           'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                           'owner_id': owner.id if owner is not None else 0,
                           'pk': self.treatment_plan.pk
                       })


class TreatmentMedicationUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование лекарства в плане лечения
    """
    model = TreatmentMedication
    form_class = TreatmentMedicationWithScheduleForm
    template_name = 'treatment_management/medication_form.html'
    
    def get_owner_from_plan(self, plan):
        """Получает владельца плана лечения"""
        if getattr(plan, 'patient_department_status_id', None):
            return plan.patient_department_status
        if getattr(plan, 'encounter_id', None):
            return plan.encounter
        return getattr(plan, 'owner', None)
    
    def get_patient_from_owner(self, owner):
        """Получает пациента из владельца"""
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None
    
    def form_valid(self, form):
        response = super().form_valid(form)  # Сохраняем TreatmentMedication
        
        # Обновляем расписание, если оно включено
        if form.cleaned_data.get('enable_schedule'):
            try:
                # Сначала удаляем существующие записи расписания
                from clinical_scheduling.models import ScheduledAppointment
                from django.contrib.contenttypes.models import ContentType
                
                content_type = ContentType.objects.get_for_model(form.instance)
                ScheduledAppointment.objects.filter(
                    content_type=content_type,
                    object_id=form.instance.pk
                ).delete()
                
                # Затем создаем новое расписание
                from clinical_scheduling.services import ClinicalSchedulingService
                ClinicalSchedulingService.create_schedule_for_assignment(
                    assignment=form.instance,
                    user=self.request.user,
                    start_date=form.cleaned_data['start_date'],
                    first_time=form.cleaned_data['first_time'],
                    times_per_day=form.cleaned_data['times_per_day'],
                    duration_days=form.cleaned_data['duration_days']
                )
                messages.success(self.request, _('Лекарство и расписание успешно обновлены.'))
            except Exception as e:
                messages.warning(self.request, _('Лекарство обновлено, но возникла ошибка при обновлении расписания: {}').format(str(e)))
        else:
            # Если расписание отключено, удаляем существующие записи
            try:
                from clinical_scheduling.models import ScheduledAppointment
                from django.contrib.contenttypes.models import ContentType
                
                content_type = ContentType.objects.get_for_model(form.instance)
                ScheduledAppointment.objects.filter(
                    content_type=content_type,
                    object_id=form.instance.pk
                ).delete()
                messages.success(self.request, _('Лекарство обновлено, расписание отключено.'))
            except Exception as e:
                messages.warning(self.request, _('Лекарство обновлено, но возникла ошибка при отключении расписания: {}').format(str(e)))
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        owner = self.get_owner_from_plan(self.object.treatment_plan)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['title'] = _('Редактировать лекарство')
        
        # Получаем пациента
        context['patient'] = self.get_patient_from_owner(owner) if owner is not None else None
        
        return context
    
    def get_success_url(self):
        owner = self.get_owner_from_plan(self.object.treatment_plan)
        return reverse('treatment_management:plan_detail',
                       kwargs={
                           'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                           'owner_id': owner.id if owner is not None else 0,
                           'pk': self.object.treatment_plan.pk
                       })


class TreatmentMedicationDeleteView(LoginRequiredMixin, DeleteView):
    """
    Отмена назначения лекарства из плана лечения
    """
    model = TreatmentMedication
    template_name = 'treatment_management/medication_confirm_delete.html'
    
    def get_owner_from_plan(self, plan):
        """Получает владельца плана лечения"""
        if getattr(plan, 'patient_department_status_id', None):
            return plan.patient_department_status
        if getattr(plan, 'encounter_id', None):
            return plan.encounter
        return getattr(plan, 'owner', None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        # Получаем владельца через план лечения
        owner = self.get_owner_from_plan(self.object.treatment_plan)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['title'] = _('Отменить назначение лекарства')
        
        # Проверяем возможность отмены
        can_cancel, error_message = self.object.can_be_cancelled()
        context['can_be_cancelled'] = can_cancel
        context['warning_message'] = error_message
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Переопределяем метод delete для отмены назначения
        """
        self.object = self.get_object()
        
        # Проверяем возможность отмены
        can_cancel, error_message = self.object.can_be_cancelled()
        if not can_cancel:
            messages.error(request, error_message)
            return redirect(self.get_success_url())
        
        # Отменяем назначение
        try:
            self.object.cancel(
                reason="Отменено через веб-интерфейс",
                cancelled_by=request.user
            )
            messages.success(request, _('Назначение лекарства успешно отменено'))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, _('Ошибка при отмене назначения: {}').format(str(e)))
        
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        owner = self.get_owner_from_plan(self.object.treatment_plan)
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                          'owner_id': owner.id if owner is not None else 0,
                          'pk': self.object.treatment_plan.pk
                      })


class QuickAddMedicationView(LoginRequiredMixin, OwnerContextMixin, CreateView):
    """
    Быстрое добавление рекомендованного лекарства с поддержкой расписания
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
        
        # Сохраняем лекарство
        medication = form.save()
        
        # Проверяем, включено ли расписание
        enable_schedule = form.cleaned_data.get('enable_schedule', False)
        
        if enable_schedule:
            # Получаем данные расписания
            start_date = form.cleaned_data.get('start_date')
            first_time = form.cleaned_data.get('first_time')
            times_per_day = form.cleaned_data.get('times_per_day')
            duration_days = form.cleaned_data.get('duration_days')
            
            if all([start_date, first_time, times_per_day, duration_days]):
                try:
                    # Создаем расписание сразу
                    from clinical_scheduling.services import ClinicalSchedulingService
                    ClinicalSchedulingService.create_schedule_for_assignment(
                        assignment=medication,
                        user=self.request.user,
                        start_date=start_date,
                        first_time=first_time,
                        times_per_day=times_per_day,
                        duration_days=duration_days
                    )
                    messages.success(self.request, _('Лекарство и расписание успешно созданы.'))
                except Exception as e:
                    messages.warning(self.request, _('Лекарство создано, но возникла ошибка при создании расписания: {}').format(str(e)))
            else:
                messages.warning(self.request, _('Лекарство создано, но не все поля расписания заполнены.'))
        else:
            messages.success(self.request, _('Лекарство успешно добавлено в план лечения.'))
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        owner = self.resolve_owner_from_plan(self.treatment_plan)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['recommended_medication'] = self.recommended_medication
        context['title'] = _('Быстрое добавление лекарства')
        
        # Получаем пациента через миксин
        context['patient'] = self.get_patient_from_owner(owner) if owner is not None else None
        
        return context
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.treatment_plan)
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                          'owner_id': owner.id if owner is not None else 0,
                          'pk': self.treatment_plan.pk
                      })



@method_decorator(csrf_exempt, name='dispatch')
class MedicationInfoView(LoginRequiredMixin, View):
    """AJAX endpoint для получения информации о препарате"""
    
    def get(self, request, medication_id):
        try:
            from pharmacy.models import Medication, Regimen, DosingInstruction, PopulationCriteria
            from datetime import date
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
                'medication_form': getattr(medication, 'medication_form', ''),
                'dosage': '',
                'frequency': '',
                'route': None,  # Теперь это будет ID AdministrationMethod
                'duration': '',
                'instructions': ''
            }
            
            # Получаем торговые названия с подробной информацией и схемами применения
            trade_names = medication.trade_names.all().select_related('release_form', 'medication_group')
            if trade_names.exists():
                # Собираем информацию о всех доступных формах с их схемами
                available_forms = []
                for tn in trade_names:
                    # Получаем все подходящие схемы для пациента (без фильтрации по форме выпуска)
                    suitable_regimens = Regimen.objects.get_suitable_for_patient(
                        medication=medication, 
                        patient=patient
                    ).prefetch_related('dosing_instructions', 'dosing_instructions__route')
                    
                    # Используем все подходящие схемы (не фильтруем по форме выпуска)
                    compatible_regimens = suitable_regimens
                    
                    # Собираем информацию о схемах
                    regimens_info = []
                    
                    for regimen in compatible_regimens:
                        dosing_instruction = regimen.dosing_instructions.first()
                        
                        if dosing_instruction:
                            regimen_info = {
                                'id': regimen.id,
                                'name': regimen.name,
                                'notes': regimen.notes or '',
                                'dosage': dosing_instruction.dose_description,
                                'frequency': dosing_instruction.frequency_description,
                                'route': map_route_to_form_value(dosing_instruction.route.name if dosing_instruction.route else None),
                                'route_name': dosing_instruction.route.name if dosing_instruction.route else 'Не указан',
                                'duration': dosing_instruction.duration_description,
                                'instructions': regimen.notes or ''
                            }
                            regimens_info.append(regimen_info)
                    
                    form_info = {
                        'id': tn.id,
                        'name': tn.name,
                        'group': tn.medication_group.name if tn.medication_group else None,
                        'release_form': {
                            'name': tn.release_form.name if tn.release_form else None,
                            'description': tn.release_form.description if tn.release_form else None
                        } if tn.release_form else None,
                        'external_url': tn.external_info_url or medication.external_info_url or '',
                        'atc_code': tn.atc_code,
                        'regimens': regimens_info  # Добавляем схемы применения
                    }
                    available_forms.append(form_info)
                
                medication_info['available_forms'] = available_forms
                
                # Если есть торговые названия, используем первое для получения дополнительной информации
                first_trade_name = trade_names.first()
                if first_trade_name:
                    medication_info.update({
                        'trade_name': first_trade_name.name,
                        'generic_concept': first_trade_name.medication.name,
                        'external_url': first_trade_name.external_info_url or medication.external_info_url or '',
                        'medication_form': getattr(first_trade_name.release_form, 'name', '') if first_trade_name.release_form else medication_info['medication_form'],
                        'selected_form_id': first_trade_name.id  # ID выбранной формы по умолчанию
                    })
                    
                    # Добавляем схемы для первой формы по умолчанию
                    if available_forms and available_forms[0]['regimens']:
                        first_regimen = available_forms[0]['regimens'][0]
                        medication_info.update({
                            'dosage': first_regimen['dosage'],
                            'frequency': first_regimen['frequency'],
                            'route': first_regimen['route'],  # ID для ForeignKey поля
                            'route_name': first_regimen['route_name'],  # Название для отображения
                            'duration': first_regimen['duration'],
                            'instructions': first_regimen['instructions']
                        })
            else:
                # Если торговых наименований нет, используем базовую информацию
                medication_info.update({
                    'trade_name': None,
                    'generic_concept': medication.name,
                    'available_forms': []
                })
            
            # Получаем стандартные дозировки с учетом пациента через оптимизированный менеджер
            suitable_regimens = Regimen.objects.get_suitable_for_patient(
                medication=medication, 
                patient=patient
            ).prefetch_related('dosing_instructions', 'dosing_instructions__route')
            
            regimen = suitable_regimens.first()
            
            if regimen:
                dosing_instruction = regimen.dosing_instructions.first()
                if dosing_instruction:
                    medication_info.update({
                        'dosage': dosing_instruction.dose_description,
                        'frequency': dosing_instruction.frequency_description,
                        'route': map_route_to_form_value(dosing_instruction.route.name if dosing_instruction.route else None),
                        'route_name': dosing_instruction.route.name if dosing_instruction.route else 'Не указан',
                        'duration': dosing_instruction.duration_description,
                        'instructions': regimen.notes or ''
                    })
            
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


@method_decorator(csrf_exempt, name='dispatch')
class TradeNameInfoView(LoginRequiredMixin, View):
    """AJAX endpoint для получения информации о конкретной торговой форме препарата"""
    
    def get(self, request, trade_name_id):
        try:
            from pharmacy.models import TradeName
            trade_name = TradeName.objects.select_related('release_form', 'medication_group', 'medication').get(pk=trade_name_id)
            
            # Получаем информацию о пациенте из параметров запроса
            patient_id = request.GET.get('patient_id')
            patient = None
            if patient_id:
                from patients.models import Patient
                try:
                    patient = Patient.objects.get(pk=patient_id)
                except Patient.DoesNotExist:
                    pass
            
            # Используем общую функцию map_route_to_form_value
            
            # Получаем информацию о торговой форме
            form_info = {
                'id': trade_name.id,
                'name': trade_name.name,
                'medication_name': trade_name.medication.name,
                'group': trade_name.medication_group.name if trade_name.medication_group else None,
                'release_form': {
                    'name': trade_name.release_form.name if trade_name.release_form else None,
                    'description': trade_name.release_form.description if trade_name.release_form else None
                } if trade_name.release_form else None,
                'external_url': trade_name.external_info_url or trade_name.medication.external_info_url or '',
                'atc_code': trade_name.atc_code,
                'dosage': '',
                'frequency': '',
                'route': None,  # Теперь это будет ID AdministrationMethod
                'duration': '',
                'instructions': ''
            }
            
            # Получаем схемы применения, совместимые с этой формой через оптимизированный менеджер
            from pharmacy.models import Regimen
            
            # Получаем все подходящие схемы для пациента (без фильтрации по форме выпуска)
            suitable_regimens = Regimen.objects.get_suitable_for_patient(
                medication=trade_name.medication, 
                patient=patient
            ).prefetch_related('dosing_instructions', 'dosing_instructions__route')
            
            # Используем все подходящие схемы (не фильтруем по форме выпуска)
            compatible_regimens = suitable_regimens
            
            # Собираем информацию о схемах
            all_regimens_info = []
            for regimen in compatible_regimens:
                dosing_instruction = regimen.dosing_instructions.first()
                if dosing_instruction:
                    regimen_info = {
                        'id': regimen.id,
                        'name': regimen.name,
                        'notes': regimen.notes or '',
                        'dosage': dosing_instruction.dose_description,
                        'frequency': dosing_instruction.frequency_description,
                        'route': map_route_to_form_value(dosing_instruction.route.name if dosing_instruction.route else None),
                        'route_name': dosing_instruction.route.name if dosing_instruction.route else 'Не указан',
                        'duration': dosing_instruction.duration_description,
                        'instructions': regimen.notes or '',
                        'is_suitable': True  # Все схемы уже отфильтрованы менеджером
                    }
                    all_regimens_info.append(regimen_info)
            
            # Все схемы уже подходящие для пациента (отфильтрованы менеджером)
            suitable_regimens = all_regimens_info
            
            # Добавляем все схемы в информацию о форме
            form_info['all_regimens'] = all_regimens_info
            form_info['suitable_regimens'] = suitable_regimens
            
            # Если есть подходящие схемы, используем первую для заполнения полей по умолчанию
            if suitable_regimens:
                first_suitable = suitable_regimens[0]
                form_info.update({
                    'dosage': first_suitable['dosage'],
                    'frequency': first_suitable['frequency'],
                    'route': first_suitable['route'],
                    'route_name': first_suitable['route_name'],  # Добавляем название для отображения
                    'duration': first_suitable['duration'],
                    'instructions': first_suitable['instructions'],
                    'selected_regimen_id': first_suitable['id']
                })
            elif all_regimens_info:
                # Если нет подходящих, используем первую доступную
                first_available = all_regimens_info[0]
                form_info.update({
                    'dosage': first_available['dosage'],
                    'frequency': first_available['frequency'],
                    'route': first_available['route'],
                    'route_name': first_available['route_name'],  # Добавляем название для отображения
                    'duration': first_available['duration'],
                    'instructions': first_available['instructions'],
                    'selected_regimen_id': first_available['id']
                })
            
            return JsonResponse({
                'success': True,
                'form_info': form_info
            })
            
        except TradeName.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Торговая форма не найдена'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                    'error': str(e)
                }, status=500)


class TreatmentRecommendationCreateView(LoginRequiredMixin, CreateView):
    """
    Создание новой рекомендации в плане лечения
    """
    model = TreatmentRecommendation
    form_class = TreatmentRecommendationForm
    template_name = 'treatment_management/recommendation_form.html'
    
    def resolve_owner_from_plan(self, plan):
        """Получает владельца плана лечения"""
        if getattr(plan, 'patient_department_status_id', None):
            return plan.patient_department_status
        if getattr(plan, 'encounter_id', None):
            return plan.encounter
        return getattr(plan, 'owner', None)
    
    def dispatch(self, request, *args, **kwargs):
        # Получаем план лечения из URL параметров
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)
        
        # Если включено расписание, создаем ScheduledAppointment
        if form.cleaned_data.get('enable_schedule'):
            try:
                self.create_scheduled_appointments(form.cleaned_data)
                messages.success(self.request, _('Рекомендация успешно добавлена с расписанием'))
            except Exception as e:
                messages.warning(self.request, _('Рекомендация добавлена, но не удалось создать расписание: {}').format(str(e)))
        else:
            messages.success(self.request, _('Рекомендация успешно добавлена'))
        
        return response
    
    def create_scheduled_appointments(self, cleaned_data):
        """Создает запланированные события для рекомендации"""
        from clinical_scheduling.services import ClinicalSchedulingService
        from departments.models import Department
        
        # Получаем пациента и отделение из плана лечения
        if self.treatment_plan.patient_department_status:
            # Если план связан с отделением
            patient = self.treatment_plan.patient_department_status.patient
            department = self.treatment_plan.patient_department_status.department
        elif self.treatment_plan.encounter:
            # Если план связан с encounter
            encounter = self.treatment_plan.encounter
            patient = encounter.patient
            
            # Ищем активный статус пациента в отделении
            from departments.models import PatientDepartmentStatus
            active_status = PatientDepartmentStatus.objects.filter(
                patient=patient,
                status='accepted'
            ).first()
            
            if active_status:
                department = active_status.department
            else:
                # Используем отделение по умолчанию
                department = Department.objects.filter(slug='admission').first()
        else:
            raise ValueError("План лечения должен быть связан с отделением или encounter")
        
        if not patient or not department:
            raise ValueError("Не удалось определить пациента или отделение")
        
        # Передаем encounter только если он доступен
        encounter_param = None
        if self.treatment_plan.encounter:
            encounter_param = self.treatment_plan.encounter
        
        ClinicalSchedulingService.create_schedule_for_recommendation(
            recommendation=self.object,
            patient=patient,
            department=department,
            start_date=cleaned_data['start_date'],
            first_time=cleaned_data['first_time'],
            times_per_day=cleaned_data['times_per_day'],
            duration_days=cleaned_data['duration_days'],
            encounter=encounter_param
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        
        # Получаем владельца и пациента для контекста
        owner = self.resolve_owner_from_plan(self.treatment_plan)
        context['owner'] = owner
        
        # Убеждаемся, что у нас есть валидный владелец
        if owner is not None:
            context['owner_model'] = owner._meta.model_name
            context['owner_id'] = owner.id
        else:
            # Fallback - используем encounter если есть
            if hasattr(self.treatment_plan, 'encounter') and self.treatment_plan.encounter:
                context['owner'] = self.treatment_plan.encounter
                context['owner_model'] = 'encounter'
                context['owner_id'] = self.treatment_plan.encounter.id
            else:
                context['owner_model'] = 'unknown'
                context['owner_id'] = 0
        
        # Получаем пациента
        if context['owner'] is not None:
            if hasattr(context['owner'], 'patient'):
                context['patient'] = context['owner'].patient
            elif hasattr(context['owner'], 'get_patient'):
                context['patient'] = context['owner'].get_patient()
            else:
                context['patient'] = None
        else:
            context['patient'] = None
        
        # Добавляем encounter для обратной совместимости
        if hasattr(self.treatment_plan, 'encounter') and self.treatment_plan.encounter:
            context['encounter'] = self.treatment_plan.encounter
        
        context['title'] = _('Добавить рекомендацию')
        
        return context
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.treatment_plan)
        if owner is None:
            # Fallback - используем encounter если есть
            if hasattr(self.treatment_plan, 'encounter') and self.treatment_plan.encounter:
                return reverse('treatment_management:plan_detail',
                              kwargs={
                                  'owner_model': 'encounter',
                                  'owner_id': self.treatment_plan.encounter.id,
                                  'pk': self.treatment_plan.pk
                              })
            else:
                # Если ничего не найдено, возвращаемся к списку планов
                return reverse('treatment_management:plan_list')
        
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': owner._meta.model_name,
                          'owner_id': owner.id,
                          'pk': self.treatment_plan.pk
                      })


class TreatmentRecommendationUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование рекомендации в плане лечения
    """
    model = TreatmentRecommendation
    form_class = TreatmentRecommendationForm
    template_name = 'treatment_management/recommendation_form.html'
    
    def resolve_owner_from_plan(self, plan):
        """Получает владельца плана лечения"""
        if getattr(plan, 'patient_department_status_id', None):
            return plan.patient_department_status
        if getattr(plan, 'encounter_id', None):
            return plan.encounter
        return getattr(plan, 'owner', None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        
        # Получаем владельца и пациента для контекста
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        context['owner'] = owner
        
        # Убеждаемся, что у нас есть валидный владелец
        if owner is not None:
            context['owner_model'] = owner._meta.model_name
            context['owner_id'] = owner.id
        else:
            # Fallback - используем encounter если есть
            if hasattr(self.object.treatment_plan, 'encounter') and self.object.treatment_plan.encounter:
                context['owner'] = self.object.treatment_plan.encounter
                context['owner_model'] = 'encounter'
                # Проверяем, что encounter.id действительно существует и не пустой
                encounter_id = getattr(self.object.treatment_plan.encounter, 'id', None)
                if encounter_id is not None and encounter_id != '':
                    context['owner_id'] = encounter_id
                else:
                    # Если encounter.id пустой, используем pk
                    context['owner_id'] = self.object.treatment_plan.encounter.pk
            else:
                context['owner_model'] = 'unknown'
                context['owner_id'] = 0
        
        # Получаем пациента
        if context['owner'] is not None:
            if hasattr(context['owner'], 'patient'):
                context['patient'] = context['owner'].patient
            elif hasattr(context['owner'], 'get_patient'):
                context['patient'] = context['owner'].get_patient()
            else:
                context['patient'] = None
        else:
            context['patient'] = None
        
        # Добавляем encounter для обратной совместимости
        if hasattr(self.object.treatment_plan, 'encounter') and self.object.treatment_plan.encounter:
            context['encounter'] = self.object.treatment_plan.encounter
        
        context['title'] = _('Редактировать рекомендацию')
        
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Если включено расписание, обновляем или создаем ScheduledAppointment
        if form.cleaned_data.get('enable_schedule'):
            try:
                self.update_scheduled_appointments(form.cleaned_data)
                messages.success(self.request, _('Рекомендация успешно обновлена с расписанием'))
            except Exception as e:
                messages.warning(self.request, _('Рекомендация обновлена, но не удалось обновить расписание: {}').format(str(e)))
        else:
            # Если расписание отключено, удаляем существующие ScheduledAppointment
            try:
                self.remove_scheduled_appointments()
                messages.success(self.request, _('Рекомендация успешно обновлена, расписание удалено'))
            except Exception as e:
                messages.warning(self.request, _('Рекомендация обновлена, но не удалось удалить расписание: {}').format(str(e)))
        
        return response
    
    def update_scheduled_appointments(self, cleaned_data):
        """Обновляет или создает запланированные события для рекомендации"""
        from clinical_scheduling.services import ClinicalSchedulingService
        from departments.models import Department
        
        # Сначала удаляем существующие записи
        self.remove_scheduled_appointments()
        
        # Получаем пациента и отделение из плана лечения
        if self.object.treatment_plan.patient_department_status:
            # Если план связан с отделением
            patient = self.object.treatment_plan.patient_department_status.patient
            department = self.object.treatment_plan.patient_department_status.department
        elif self.object.treatment_plan.encounter:
            # Если план связан с encounter
            encounter = self.object.treatment_plan.encounter
            patient = encounter.patient
            
            # Ищем активный статус пациента в отделении
            from departments.models import PatientDepartmentStatus
            active_status = PatientDepartmentStatus.objects.filter(
                patient=patient,
                status='accepted'
            ).first()
            
            if active_status:
                department = active_status.department
            else:
                # Используем отделение по умолчанию
                department = Department.objects.filter(slug='admission').first()
        else:
            raise ValueError("План лечения должен быть связан с отделением или encounter")
        
        if not patient or not department:
            raise ValueError("Не удалось определить пациента или отделение")
        
        # Создаем новое расписание
        # Передаем encounter только если он доступен
        encounter_param = None
        if self.object.treatment_plan.encounter:
            encounter_param = self.object.treatment_plan.encounter
        
        ClinicalSchedulingService.create_schedule_for_recommendation(
            recommendation=self.object,
            patient=patient,
            department=department,
            start_date=cleaned_data['start_date'],
            first_time=cleaned_data['first_time'],
            times_per_day=cleaned_data['times_per_day'],
            duration_days=cleaned_data['duration_days'],
            encounter=encounter_param
        )
    
    def remove_scheduled_appointments(self):
        """Удаляет существующие запланированные события для рекомендации"""
        from clinical_scheduling.models import ScheduledAppointment
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(self.object)
        ScheduledAppointment.objects.filter(
            content_type=content_type,
            object_id=self.object.id
        ).delete()
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        if owner is None:
            # Fallback - используем encounter если есть
            if hasattr(self.object.treatment_plan, 'encounter') and self.object.treatment_plan.encounter:
                return reverse('treatment_management:plan_detail',
                              kwargs={
                                  'owner_model': 'encounter',
                                  'owner_id': self.object.treatment_plan.encounter.id,
                                  'pk': self.object.treatment_plan.pk
                              })
            else:
                # Если ничего не найдено, возвращаемся к списку планов
                return reverse('treatment_management:plan_list')
        
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': owner._meta.model_name,
                          'owner_id': owner.id,
                          'pk': self.object.treatment_plan.pk
                      })


class TreatmentRecommendationDeleteView(LoginRequiredMixin, DeleteView):
    """
    Отмена рекомендации из плана лечения
    """
    model = TreatmentRecommendation
    template_name = 'treatment_management/recommendation_confirm_delete.html'
    
    def resolve_owner_from_plan(self, plan):
        """Получает владельца плана лечения"""
        if getattr(plan, 'patient_department_status_id', None):
            return plan.patient_department_status
        if getattr(plan, 'encounter_id', None):
            return plan.encounter
        return getattr(plan, 'owner', None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        
        # Получаем владельца и пациента для контекста
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        context['owner'] = owner
        
        # Убеждаемся, что у нас есть валидный владелец
        if owner:
            context['owner_model'] = owner._meta.model_name
            context['owner_id'] = owner.id
        else:
            context['owner_model'] = 'unknown'
            context['owner_id'] = 0
        
        context['title'] = _('Отменить рекомендацию')
        
        # Проверяем возможность отмены
        can_cancel, error_message = self.object.can_be_cancelled()
        context['can_be_cancelled'] = can_cancel
        context['warning_message'] = error_message
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Переопределяем метод delete для отмены рекомендации
        """
        self.object = self.get_object()
        
        # Проверяем возможность отмены
        can_cancel, error_message = self.object.can_be_cancelled()
        if not can_cancel:
            messages.error(request, error_message)
            return redirect(self.get_success_url())
        
        # Отменяем рекомендацию
        try:
            self.object.cancel(
                reason="Отменено через веб-интерфейс",
                cancelled_by=request.user
            )
            messages.success(request, _('Рекомендация успешно отменена'))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, _('Ошибка при отмене рекомендации: {}').format(str(e)))
        
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        if owner is None:
            # Fallback - используем encounter если есть
            if hasattr(self.object.treatment_plan, 'encounter') and self.object.treatment_plan.encounter:
                return reverse('treatment_management:plan_detail',
                              kwargs={
                                  'owner_model': 'encounter',
                                  'owner_id': self.object.treatment_plan.encounter.id,
                                  'pk': self.object.treatment_plan.pk
                              })
            else:
                # Если ничего не найдено, возвращаемся к списку планов
                return reverse('treatment_management:plan_list')
        
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': owner._meta.model_name,
                          'owner_id': owner.id,
                          'pk': self.object.treatment_plan.pk
                      })


class TreatmentPlanQuickCreateView(LoginRequiredMixin, View):
	"""
	Быстрое создание плана лечения для Encounter:
	- если планы есть — перейти к списку планов
	- если планов нет — создать "Основной" и перейти на его детальную страницу
	"""
	def get(self, request, *args, **kwargs):
		from encounters.models import Encounter
		encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
		plans_qs = TreatmentPlanService.get_treatment_plans(encounter)
		if plans_qs.exists():
			return redirect('treatment_management:plan_list', owner_model='encounter', owner_id=encounter.pk)
		plan = TreatmentPlanService.create_treatment_plan(
			owner=encounter,
			name='Основной',
			description='Стандартный план лечения',
			created_by=request.user,
		)
		return redirect('treatment_management:plan_detail', owner_model='encounter', owner_id=encounter.pk, pk=plan.pk)



