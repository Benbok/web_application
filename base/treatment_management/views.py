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

from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation
from .forms import TreatmentPlanForm, TreatmentMedicationForm, QuickAddMedicationForm, TreatmentRecommendationForm
from .services import (
    TreatmentPlanService, TreatmentMedicationService, TreatmentRecommendationService
)
from patients.models import Patient

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
    
    def get_queryset(self):
        # Настраиваем контекст владельца
        self.setup_owner_context()
        return TreatmentPlanService.get_treatment_plans(self.owner)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
        context['patient'] = self.patient
        
        # Автоматически создаем основной план лечения, если его нет
        if not self.object_list.exists():
            TreatmentPlan.get_or_create_main_plan(self.owner)
            # Обновляем queryset
            self.object_list = TreatmentPlanService.get_treatment_plans(self.owner)
        
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner = self.resolve_owner_from_plan(self.object)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['medications'] = self.object.medications.all()
        context['recommendations'] = self.object.recommendations.all()
        
        # Получаем пациента через миксин
        context['patient'] = self.get_patient_from_owner(owner) if owner is not None else None
        
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
    Удаление плана лечения
    """
    model = TreatmentPlan
    template_name = 'treatment_management/plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owner = self.resolve_owner_from_plan(self.object)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['medications'] = self.object.medications.all()
        context['title'] = _('Удалить план лечения')
        return context
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.object)
        return reverse('treatment_management:plan_list',
                       kwargs={
                           'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                           'owner_id': owner.id if owner is not None else 0
                       })


class TreatmentMedicationCreateView(LoginRequiredMixin, OwnerContextMixin, CreateView):
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


class TreatmentMedicationUpdateView(LoginRequiredMixin, OwnerContextMixin, UpdateView):
    """
    Редактирование лекарства в плане лечения
    """
    model = TreatmentMedication
    form_class = TreatmentMedicationForm
    template_name = 'treatment_management/medication_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['title'] = _('Редактировать лекарство')
        
        # Получаем пациента через миксин
        context['patient'] = self.get_patient_from_owner(owner) if owner is not None else None
        
        return context
    
    def get_success_url(self):
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        return reverse('treatment_management:plan_detail',
                       kwargs={
                           'owner_model': owner._meta.model_name if owner is not None else 'unknown',
                           'owner_id': owner.id if owner is not None else 0,
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
        owner = self.resolve_owner_from_plan(self.object.treatment_plan)
        context['owner'] = owner
        context['owner_model'] = owner._meta.model_name if owner is not None else 'unknown'
        context['title'] = _('Удалить лекарство')
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.object.treatment_plan.owner._meta.model_name,
                          'owner_id': self.object.treatment_plan.owner.id,
                          'pk': self.object.treatment_plan.pk
                      })


class QuickAddMedicationView(LoginRequiredMixin, OwnerContextMixin, CreateView):
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
        
        # Получаем пациента через миксин
        context['patient'] = self.get_patient_from_owner(self.treatment_plan.owner)
        
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.treatment_plan.owner._meta.model_name,
                          'owner_id': self.treatment_plan.owner.id,
                          'pk': self.treatment_plan.pk
                      })



@method_decorator(csrf_exempt, name='dispatch')
class MedicationInfoView(View):
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
class TradeNameInfoView(View):
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
    
    def dispatch(self, request, *args, **kwargs):
        # Получаем план лечения из URL параметров
        self.treatment_plan = get_object_or_404(TreatmentPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.treatment_plan = self.treatment_plan
        response = super().form_valid(form)
        messages.success(self.request, _('Рекомендация успешно добавлена'))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.treatment_plan
        context['title'] = _('Добавить рекомендацию')
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.treatment_plan.owner._meta.model_name,
                          'owner_id': self.treatment_plan.owner.id,
                          'pk': self.treatment_plan.pk
                      })


class TreatmentRecommendationUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование рекомендации в плане лечения
    """
    model = TreatmentRecommendation
    form_class = TreatmentRecommendationForm
    template_name = 'treatment_management/recommendation_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['title'] = _('Редактировать рекомендацию')
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.object.treatment_plan.owner._meta.model_name,
                          'owner_id': self.object.treatment_plan.owner.id,
                          'pk': self.object.treatment_plan.pk
                      })


class TreatmentRecommendationDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление рекомендации из плана лечения
    """
    model = TreatmentRecommendation
    template_name = 'treatment_management/recommendation_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_plan'] = self.object.treatment_plan
        context['title'] = _('Удалить рекомендацию')
        return context
    
    def get_success_url(self):
        return reverse('treatment_management:plan_detail',
                      kwargs={
                          'owner_model': self.object.treatment_plan.owner._meta.model_name,
                          'owner_id': self.object.treatment_plan.owner.id,
                          'pk': self.object.treatment_plan.pk
        })
