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
        
        # Автоматически создаем основной план лечения, если его нет
        if not self.object_list.exists():
            TreatmentPlan.get_or_create_main_plan(self.owner)
            # Обновляем queryset
            self.object_list = TreatmentPlanService.get_treatment_plans(self.owner)
        
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
        context['recommendations'] = self.object.recommendations.all()
        
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



@method_decorator(csrf_exempt, name='dispatch')
class MedicationInfoView(View):
    """AJAX endpoint для получения информации о препарате"""
    
    def get(self, request, medication_id):
        try:
            from pharmacy.models import Medication, Regimen, DosingInstruction, PopulationCriteria
            from datetime import date
            medication = Medication.objects.get(pk=medication_id)
            
            # Функция для преобразования текстового способа введения в код для формы
            def map_route_to_form_value(route_text):
                if not route_text:
                    return 'oral'
                
                route_lower = route_text.lower()
                if 'ректально' in route_lower:
                    return 'rectal'
                elif 'местно' in route_lower:
                    return 'topical'
                elif 'перорально' in route_lower or 'внутрь' in route_lower:
                    return 'oral'
                elif 'внутримышечно' in route_lower:
                    return 'intramuscular'
                elif 'внутривенно' in route_lower:
                    return 'intravenous'
                elif 'подкожно' in route_lower:
                    return 'subcutaneous'
                elif 'ингаляционно' in route_lower:
                    return 'inhalation'
                else:
                    return 'other'
            
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
                'route': 'oral',
                'duration': '',
                'instructions': ''
            }
            
            # Получаем торговые названия с подробной информацией и схемами применения
            trade_names = medication.trade_names.all().select_related('release_form', 'medication_group')
            if trade_names.exists():
                # Собираем информацию о всех доступных формах с их схемами
                available_forms = []
                for tn in trade_names:
                    # Получаем схемы применения для этой формы
                    regimens = Regimen.objects.filter(
                        medication=medication,
                        dosing_instructions__isnull=False
                    ).distinct()
                    
                    # Фильтруем схемы по совместимости с формой
                    compatible_regimens = []
                    for regimen in regimens:
                        dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
                        if dosing_instruction:
                            # Если поле route не заполнено, считаем схему совместимой со всеми формами
                            if not dosing_instruction.route:
                                compatible_regimens.append(regimen)
                                continue
                            
                            # Если поле route заполнено, проверяем совместимость
                            route = dosing_instruction.route.name.lower()
                            release_form = tn.release_form.name.lower() if tn.release_form else ''
                            
                            # Проверяем совместимость формы и схемы
                            is_compatible = False
                            if 'суппозитории' in release_form and 'ректально' in route:
                                is_compatible = True
                            elif 'гель' in release_form and 'местно' in route:
                                is_compatible = True
                            elif 'мазь' in release_form and 'местно' in route:
                                is_compatible = True
                            elif 'таблетки' in release_form and 'перорально' in route:
                                is_compatible = True
                            elif 'инъекции' in release_form and ('внутримышечно' in route or 'внутривенно' in route):
                                is_compatible = True
                            else:
                                # Если не можем определить совместимость, считаем совместимым
                                is_compatible = True
                            
                            if is_compatible:
                                compatible_regimens.append(regimen)
                    
                    # Получаем схемы с учетом возраста пациента
                    suitable_regimens = []
                    if patient and patient.birth_date:
                        age_days = (date.today() - patient.birth_date).days
                        
                        for regimen in compatible_regimens:
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
                    else:
                        # Если нет информации о пациенте, берем совместимые схемы
                        suitable_regimens = compatible_regimens
                    
                    # Собираем информацию о схемах
                    regimens_info = []
                    for regimen in suitable_regimens:
                        dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
                        if dosing_instruction:
                            regimen_info = {
                                'id': regimen.id,
                                'name': regimen.name,
                                'notes': regimen.notes or '',
                                'dosage': dosing_instruction.dose_description,
                                'frequency': dosing_instruction.frequency_description,
                                'route': map_route_to_form_value(dosing_instruction.route.name if dosing_instruction.route else 'oral'),
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
                            'route': first_regimen['route'],
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
                    medication_info.update({
                        'dosage': dosing_instruction.dose_description,
                        'frequency': dosing_instruction.frequency_description,
                        'route': map_route_to_form_value(dosing_instruction.route.name if dosing_instruction.route else 'oral'),
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
            
            # Функция для преобразования текстового способа введения в код для формы
            def map_route_to_form_value(route_text):
                if not route_text:
                    return 'oral'
                
                route_lower = route_text.lower()
                if 'ректально' in route_lower:
                    return 'rectal'
                elif 'местно' in route_lower:
                    return 'topical'
                elif 'перорально' in route_lower or 'внутрь' in route_lower:
                    return 'oral'
                elif 'внутримышечно' in route_lower:
                    return 'intramuscular'
                elif 'внутривенно' in route_lower:
                    return 'intravenous'
                elif 'подкожно' in route_lower:
                    return 'subcutaneous'
                elif 'ингаляционно' in route_lower:
                    return 'inhalation'
                else:
                    return 'other'
            
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
                'route': 'oral',
                'duration': '',
                'instructions': ''
            }
            
            # Получаем схемы применения, совместимые с этой формой
            from pharmacy.models import Regimen, DosingInstruction, PopulationCriteria
            from datetime import date
            
            # Получаем все схемы для этого препарата
            all_regimens = Regimen.objects.filter(
                medication=trade_name.medication,
                dosing_instructions__isnull=False
            ).distinct()
            
            # Фильтруем схемы по совместимости с формой
            compatible_regimens = []
            for regimen in all_regimens:
                dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
                if dosing_instruction:
                    # Если поле route не заполнено, считаем схему совместимой со всеми формами
                    if not dosing_instruction.route:
                        compatible_regimens.append(regimen)
                        continue
                    
                    # Если поле route заполнено, проверяем совместимость
                    route = dosing_instruction.route.name.lower()
                    release_form = trade_name.release_form.name.lower() if trade_name.release_form else ''
                    
                    # Проверяем совместимость формы и схемы
                    is_compatible = False
                    if 'суппозитории' in release_form and 'ректально' in route:
                        is_compatible = True
                    elif 'гель' in release_form and 'местно' in route:
                        is_compatible = True
                    elif 'мазь' in release_form and 'местно' in route:
                        is_compatible = True
                    elif 'таблетки' in release_form and 'перорально' in route:
                        is_compatible = True
                    elif 'инъекции' in release_form and ('внутримышечно' in route or 'внутривенно' in route):
                        is_compatible = True
                    else:
                        # Если не можем определить совместимость, считаем совместимым
                        is_compatible = True
                    
                    if is_compatible:
                        compatible_regimens.append(regimen)
            
            # Собираем информацию только о совместимых схемах
            all_regimens_info = []
            suitable_regimens = []
            
            for regimen in compatible_regimens:
                dosing_instruction = DosingInstruction.objects.filter(regimen=regimen).first()
                if dosing_instruction:
                    regimen_info = {
                        'id': regimen.id,
                        'name': regimen.name,
                        'notes': regimen.notes or '',
                        'dosage': dosing_instruction.dose_description,
                        'frequency': dosing_instruction.frequency_description,
                        'route': map_route_to_form_value(dosing_instruction.route.name if dosing_instruction.route else 'oral'),
                        'duration': dosing_instruction.duration_description,
                        'instructions': regimen.notes or '',
                        'is_suitable': False  # Будем определять пригодность ниже
                    }
                    all_regimens_info.append(regimen_info)
                    
                    # Проверяем пригодность для пациента
                    if patient and patient.birth_date:
                        age_days = (date.today() - patient.birth_date).days
                        
                        # Проверяем критерии населения для этой схемы
                        population_criteria = PopulationCriteria.objects.filter(regimen=regimen)
                        
                        if not population_criteria.exists():
                            # Если нет критериев, считаем подходящим
                            suitable_regimens.append(regimen_info)
                            regimen_info['is_suitable'] = True
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
                                suitable_regimens.append(regimen_info)
                                regimen_info['is_suitable'] = True
                                break
                    else:
                        # Если нет информации о пациенте, считаем все подходящими
                        suitable_regimens.append(regimen_info)
                        regimen_info['is_suitable'] = True
            
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
