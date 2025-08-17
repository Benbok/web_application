from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView
)
from django.urls import reverse, reverse_lazy
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import ExaminationPlan, ExaminationLabTest, ExaminationInstrumental
from .forms import ExaminationPlanForm, ExaminationLabTestForm, ExaminationInstrumentalForm

# Импортируем Encounter для специальных URL
try:
    from encounters.models import Encounter
except ImportError:
    Encounter = None

# Импортируем модели назначений для автоматического создания
from treatment_assignments.models import LabTestAssignment, InstrumentalProcedureAssignment


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
    
    def setup_owner_context(self):
        """
        Настраивает контекст владельца и пациента
        Должен вызываться в dispatch() или get_context_data()
        """
        if not hasattr(self, 'owner'):
            self.owner = self.get_owner()
        
        if not hasattr(self, 'patient'):
            self.patient = self.get_patient_from_owner(self.owner)


class ExaminationPlanListView(LoginRequiredMixin, ListView):
    """
    Список планов обследования для владельца
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_list.html'
    context_object_name = 'examination_plans'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
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
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None
    
    def get_queryset(self):
        # Используем GenericForeignKey для поиска планов
        return ExaminationPlan.objects.filter(
            content_type=ContentType.objects.get_for_model(self.owner),
            object_id=self.owner.id
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner_model
        context['patient'] = self.patient
        
        # Добавляем информацию о прогрессе для каждого плана
        plans_with_progress = []
        for plan in context['examination_plans']:
            progress = plan.get_overall_progress()
            plans_with_progress.append({
                'plan': plan,
                'progress': progress
            })
        context['plans_with_progress'] = plans_with_progress
        
        context['title'] = _('Планы обследования')
        return context


class ExaminationPlanCreateView(LoginRequiredMixin, CreateView):
    """
    Создание плана обследования
    """
    model = ExaminationPlan
    form_class = ExaminationPlanForm
    template_name = 'examination_management/plan_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            self.owner = self.encounter
            self.owner_model = 'encounter'
            self.patient = self.encounter.patient
        else:
            # Используем универсальный подход
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
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None
    
    def form_valid(self, form):
        # Устанавливаем владельца через GenericForeignKey
        form.instance.owner = self.owner
        
        # Для обратной совместимости, если владелец - это Encounter
        if isinstance(self.owner, Encounter):
            form.instance.encounter = self.owner
        
        response = super().form_valid(form)
        messages.success(self.request, _('План обследования успешно создан'))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner_model
        context['patient'] = self.patient
        context['title'] = _('Создать план обследования')
        return context
    
    def get_success_url(self):
        # Определяем URL в зависимости от типа владельца
        if self.owner_model == 'encounter':
            return reverse('examination_management:examination_plan_detail',
                          kwargs={
                              'encounter_pk': self.owner.id,
                              'pk': self.object.pk
                          })
        else:
            return reverse('examination_management:plan_detail',
                          kwargs={
                              'owner_model': self.owner_model,
                              'owner_id': self.owner.id,
                              'pk': self.object.pk
                          })


class ExaminationPlanUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование плана обследования
    """
    model = ExaminationPlan
    form_class = ExaminationPlanForm
    template_name = 'examination_management/plan_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем владельца через GenericForeignKey или encounter для обратной совместимости
        if hasattr(self.object, 'owner') and self.object.owner:
            context['owner'] = self.object.owner
            context['patient'] = self.get_patient_from_owner(self.object.owner)
            # Определяем тип владельца для URL
            if hasattr(self.object.owner, '_meta'):
                context['owner_model'] = self.object.owner._meta.model_name
                context['owner_id'] = self.object.owner.id
            # Если владелец - это Encounter, добавляем его в контекст
            if isinstance(self.object.owner, Encounter):
                context['encounter'] = self.object.owner
        elif hasattr(self.object, 'encounter') and self.object.encounter:
            context['encounter'] = self.object.encounter
            context['owner'] = self.object.encounter
            context['patient'] = self.object.encounter.patient
            context['owner_model'] = 'encounter'
            context['owner_id'] = self.object.encounter.id
        else:
            context['owner'] = None
            context['patient'] = None
            context['owner_model'] = None
            context['owner_id'] = None
            context['encounter'] = None
        
        context['title'] = _('Редактировать план обследования')
        return context
    
    def get_success_url(self):
        # Определяем URL в зависимости от типа владельца
        if hasattr(self.object, 'owner') and self.object.owner:
            if isinstance(self.object.owner, Encounter):
                return reverse('examination_management:examination_plan_detail',
                              kwargs={
                                  'encounter_pk': self.object.owner.id,
                                  'pk': self.object.pk
                              })
            else:
                return reverse('examination_management:plan_detail',
                              kwargs={
                                  'owner_model': self.object.owner._meta.model_name,
                                  'owner_id': self.object.owner.id,
                                  'pk': self.object.pk
                              })
        elif hasattr(self.object, 'encounter') and self.object.encounter:
            return reverse('examination_management:examination_plan_detail',
                          kwargs={
                              'encounter_pk': self.object.encounter.id,
                              'pk': self.object.pk
                          })
        else:
            # Fallback - возвращаемся к списку планов
            return reverse('examination_management:examination_plan_list',
                          kwargs={'encounter_pk': 1})  # Временное решение
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None


class ExaminationPlanDetailView(LoginRequiredMixin, DetailView):
    """
    Детальный просмотр плана обследования
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_detail.html'
    context_object_name = 'examination_plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем владельца через GenericForeignKey или encounter для обратной совместимости
        if hasattr(self.object, 'owner') and self.object.owner:
            context['owner'] = self.object.owner
            context['patient'] = self.get_patient_from_owner(self.object.owner)
            # Определяем тип владельца для URL
            if hasattr(self.object.owner, '_meta'):
                context['owner_model'] = self.object.owner._meta.model_name
                context['owner_id'] = self.object.owner.id
            # Если владелец - это Encounter, добавляем его в контекст
            if isinstance(self.object.owner, Encounter):
                context['encounter'] = self.object.owner
        elif hasattr(self.object, 'encounter') and self.object.encounter:
            context['encounter'] = self.object.encounter
            context['owner'] = self.object.encounter
            context['patient'] = self.object.encounter.patient
            context['owner_model'] = 'encounter'
            context['owner_id'] = self.object.encounter.id
        else:
            context['owner'] = None
            context['patient'] = None
            context['owner_model'] = None
            context['owner_id'] = None
            context['encounter'] = None
        
        # Получаем информацию о прогрессе плана
        progress_info = self.object.get_overall_progress()
        context['progress'] = progress_info
        
        # Получаем статусы для каждого исследования
        lab_tests_with_status = []
        for lab_test in self.object.lab_tests.all():
            status_info = self.object.get_lab_test_status(lab_test)
            lab_tests_with_status.append({
                'examination_lab_test': lab_test,
                'status_info': status_info
            })
        context['lab_tests_with_status'] = lab_tests_with_status
        
        instrumental_procedures_with_status = []
        for instrumental in self.object.instrumental_procedures.all():
            status_info = self.object.get_instrumental_procedure_status(instrumental)
            instrumental_procedures_with_status.append({
                'examination_instrumental': instrumental,
                'status_info': status_info
            })
        context['instrumental_procedures_with_status'] = instrumental_procedures_with_status
        
        return context
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None


class ExaminationPlanDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление плана обследования
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем владельца через GenericForeignKey или encounter для обратной совместимости
        if hasattr(self.object, 'owner') and self.object.owner:
            context['owner'] = self.object.owner
            context['patient'] = self.get_patient_from_owner(self.object.owner)
            # Определяем тип владельца для URL
            if hasattr(self.object.owner, '_meta'):
                context['owner_model'] = self.object.owner._meta.model_name
                context['owner_id'] = self.object.owner.id
            # Если владелец - это Encounter, добавляем его в контекст
            if isinstance(self.object.owner, Encounter):
                context['encounter'] = self.object.owner
        elif hasattr(self.object, 'encounter') and self.object.encounter:
            context['encounter'] = self.object.encounter
            context['owner'] = self.object.encounter
            context['patient'] = self.object.encounter.patient
            context['owner_model'] = 'encounter'
            context['owner_id'] = self.object.encounter.id
        else:
            context['owner'] = None
            context['patient'] = None
            context['owner_model'] = None
            context['owner_id'] = None
            context['encounter'] = None
        
        context['title'] = _('Удалить план обследования')
        return context
    
    def get_success_url(self):
        # Определяем URL в зависимости от типа владельца
        if hasattr(self.object, 'owner') and self.object.owner:
            if isinstance(self.object.owner, Encounter):
                return reverse('examination_management:examination_plan_list',
                              kwargs={'encounter_pk': self.object.owner.id})
            else:
                return reverse('examination_management:plan_list',
                              kwargs={
                                  'owner_model': self.object.owner._meta.model_name,
                                  'owner_id': self.object.owner.id
                              })
        elif hasattr(self.object, 'encounter') and self.object.encounter:
            return reverse('examination_management:examination_plan_list',
                          kwargs={'encounter_pk': self.object.encounter.id})
        else:
            # Fallback - возвращаемся к списку планов
            return reverse('examination_management:examination_plan_list',
                          kwargs={'encounter_pk': 1})  # Временное решение
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None


class ExaminationLabTestCreateView(LoginRequiredMixin, CreateView):
    """
    Добавление лабораторного исследования в план обследования
    """
    model = ExaminationLabTest
    form_class = ExaminationLabTestForm
    template_name = 'examination_management/lab_test_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.examination_plan = get_object_or_404(ExaminationPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.examination_plan = self.examination_plan
        # Сохраняем значение lab_test из формы
        form.instance.lab_test = form.cleaned_data['lab_test']
        response = super().form_valid(form)
        
        # Получаем пациента из плана обследования
        patient = None
        if hasattr(self.examination_plan, 'owner') and self.examination_plan.owner:
            patient = self.get_patient_from_owner(self.examination_plan.owner)
        elif hasattr(self.examination_plan, 'encounter') and self.examination_plan.encounter:
            patient = self.examination_plan.encounter.patient
        
        # Автоматически создаем назначение для врача-лаборанта
        if patient:
            try:
                LabTestAssignment.objects.create(
                    content_type=ContentType.objects.get_for_model(form.instance),
                    object_id=form.instance.pk,
                    patient=patient,
                    assigning_doctor=self.request.user,
                    start_date=timezone.now(),
                    lab_test=form.instance.lab_test,
                    notes=form.instance.instructions
                )
                messages.success(self.request, _('Лабораторное исследование успешно добавлено в план и назначено для выполнения'))
            except Exception as e:
                messages.warning(self.request, _('Исследование добавлено в план, но назначение не создано: {}').format(str(e)))
        else:
            messages.warning(self.request, _('Исследование добавлено в план, но пациент не найден'))
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.examination_plan
        
        # Получаем владельца и пациента
        if hasattr(self.examination_plan, 'owner') and self.examination_plan.owner:
            context['owner'] = self.examination_plan.owner
            context['patient'] = self.get_patient_from_owner(self.examination_plan.owner)
            # Определяем тип владельца для URL
            if hasattr(self.examination_plan.owner, '_meta'):
                context['owner_model'] = self.examination_plan.owner._meta.model_name
                context['owner_id'] = self.examination_plan.owner.id
            # Если владелец - это Encounter, добавляем его в контекст
            if isinstance(self.examination_plan.owner, Encounter):
                context['encounter'] = self.examination_plan.owner
        elif hasattr(self.examination_plan, 'encounter') and self.examination_plan.encounter:
            context['encounter'] = self.examination_plan.encounter
            context['owner'] = self.examination_plan.encounter
            context['patient'] = self.examination_plan.encounter.patient
            context['owner_model'] = 'encounter'
            context['owner_id'] = self.examination_plan.encounter.id
        
        context['title'] = _('Добавить лабораторное исследование')
        return context
    
    def get_success_url(self):
        # Определяем URL в зависимости от типа владельца
        if hasattr(self.examination_plan, 'owner') and self.examination_plan.owner:
            if isinstance(self.examination_plan.owner, Encounter):
                return reverse('examination_management:examination_plan_detail',
                              kwargs={
                                  'encounter_pk': self.examination_plan.owner.id,
                                  'pk': self.examination_plan.pk
                              })
            else:
                return reverse('examination_management:plan_detail',
                              kwargs={
                                  'owner_model': self.examination_plan.owner._meta.model_name,
                                  'owner_id': self.examination_plan.owner.id,
                                  'pk': self.examination_plan.pk
                              })
        else:
            # Для обратной совместимости с encounter
            return reverse('examination_management:examination_plan_detail',
                          kwargs={
                              'encounter_pk': self.examination_plan.encounter.id,
                              'pk': self.examination_plan.pk
                          })
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None


class ExaminationLabTestUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование лабораторного исследования в плане обследования
    """
    model = ExaminationLabTest
    form_class = ExaminationLabTestForm
    template_name = 'examination_management/lab_test_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        context['encounter'] = self.object.examination_plan.encounter
        context['patient'] = self.object.examination_plan.encounter.patient
        context['title'] = _('Редактировать лабораторное исследование')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.examination_plan.encounter.id,
                          'pk': self.object.examination_plan.pk
                      })


class ExaminationLabTestDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление лабораторного исследования из плана обследования
    """
    model = ExaminationLabTest
    template_name = 'examination_management/lab_test_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        # Получаем объект перед удалением
        self.object = self.get_object()
        
        # Проверяем, есть ли уже результаты у назначения
        try:
            content_type = ContentType.objects.get_for_model(self.object)
            assignment = LabTestAssignment.objects.filter(
                content_type=content_type,
                object_id=self.object.pk
            ).first()
            
            if assignment:
                # Проверяем, есть ли результаты
                from lab_tests.models import LabTestResult
                has_results = LabTestResult.objects.filter(lab_test_assignment=assignment).exists()
                
                if has_results:
                    messages.error(request, _('Нельзя удалить исследование, у которого уже есть результаты. Сначала очистите результаты в разделе лабораторных исследований.'))
                    return redirect('examination_management:plan_detail',
                                  kwargs={
                                      'owner_model': 'encounter',
                                      'owner_id': self.object.examination_plan.encounter.id,
                                      'pk': self.object.examination_plan.pk
                                  })
                else:
                    # Если результатов нет, назначение будет удалено автоматически через сигнал
                    messages.success(request, _('Лабораторное исследование и связанное назначение будут удалены'))
            else:
                messages.info(request, _('Связанное назначение не найдено'))
                
        except Exception as e:
            messages.warning(request, _('Ошибка при проверке назначения: {}').format(str(e)))
        
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        context['encounter'] = self.object.examination_plan.encounter
        context['patient'] = self.object.examination_plan.encounter.patient
        context['title'] = _('Удалить лабораторное исследование')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.examination_plan.encounter.id,
                          'pk': self.object.examination_plan.pk
                      })


class ExaminationInstrumentalCreateView(LoginRequiredMixin, CreateView):
    """
    Добавление инструментального исследования в план обследования
    """
    model = ExaminationInstrumental
    form_class = ExaminationInstrumentalForm
    template_name = 'examination_management/instrumental_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.examination_plan = get_object_or_404(ExaminationPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.examination_plan = self.examination_plan
        # Сохраняем значение instrumental_procedure из формы
        form.instance.instrumental_procedure = form.cleaned_data['instrumental_procedure']
        response = super().form_valid(form)
        
        # Получаем пациента из плана обследования
        patient = None
        if hasattr(self.examination_plan, 'owner') and self.examination_plan.owner:
            patient = self.get_patient_from_owner(self.examination_plan.owner)
        elif hasattr(self.examination_plan, 'encounter') and self.examination_plan.encounter:
            patient = self.examination_plan.encounter.patient
        
        # Автоматически создаем назначение для врача-лаборанта
        if patient:
            try:
                InstrumentalProcedureAssignment.objects.create(
                    content_type=ContentType.objects.get_for_model(form.instance),
                    object_id=form.instance.pk,
                    patient=patient,
                    assigning_doctor=self.request.user,
                    start_date=timezone.now(),
                    instrumental_procedure=form.instance.instrumental_procedure,
                    notes=form.instance.instructions
                )
                messages.success(self.request, _('Инструментальное исследование успешно добавлено в план и назначено для выполнения'))
            except Exception as e:
                messages.warning(self.request, _('Исследование добавлено в план, но назначение не создано: {}').format(str(e)))
        else:
            messages.warning(self.request, _('Исследование добавлено в план, но пациент не найден'))
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.examination_plan
        
        # Получаем владельца и пациента
        if hasattr(self.examination_plan, 'owner') and self.examination_plan.owner:
            context['owner'] = self.examination_plan.owner
            context['patient'] = self.get_patient_from_owner(self.examination_plan.owner)
        elif hasattr(self.examination_plan, 'encounter') and self.examination_plan.encounter:
            context['encounter'] = self.examination_plan.encounter
            context['owner'] = self.examination_plan.encounter
            context['patient'] = self.examination_plan.encounter.patient
        
        context['title'] = _('Добавить инструментальное исследование')
        return context
    
    def get_success_url(self):
        # Определяем URL в зависимости от типа владельца
        if hasattr(self.examination_plan, 'owner') and self.examination_plan.owner:
            owner_model = self.examination_plan.owner._meta.model_name
            owner_id = self.examination_plan.owner.id
            return reverse('examination_management:plan_detail',
                          kwargs={
                              'owner_model': owner_model,
                              'owner_id': owner_id,
                              'pk': self.examination_plan.pk
                          })
        else:
            # Для обратной совместимости с encounter
            return reverse('examination_management:plan_detail',
                          kwargs={
                              'owner_model': 'encounter',
                              'owner_id': self.examination_plan.encounter.id,
                              'pk': self.examination_plan.pk
                          })
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None


class ExaminationInstrumentalUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование инструментального исследования в плане обследования
    """
    model = ExaminationInstrumental
    form_class = ExaminationInstrumentalForm
    template_name = 'examination_management/instrumental_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        context['encounter'] = self.object.examination_plan.encounter
        context['patient'] = self.object.examination_plan.encounter.patient
        context['title'] = _('Редактировать инструментальное исследование')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.examination_plan.encounter.id,
                          'pk': self.object.examination_plan.pk
                      })


class ExaminationInstrumentalDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление инструментального исследования из плана обследования
    """
    model = ExaminationInstrumental
    template_name = 'examination_management/instrumental_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        # Получаем объект перед удалением
        self.object = self.get_object()
        
        # Проверяем, есть ли уже результаты у назначения
        try:
            content_type = ContentType.objects.get_for_model(self.object)
            assignment = InstrumentalProcedureAssignment.objects.filter(
                content_type=content_type,
                object_id=self.object.pk
            ).first()
            
            if assignment:
                # Проверяем, есть ли результаты
                from instrumental_procedures.models import InstrumentalProcedureResult
                has_results = InstrumentalProcedureResult.objects.filter(instrumental_procedure_assignment=assignment).exists()
                
                if has_results:
                    messages.error(request, _('Нельзя удалить исследование, у которого уже есть результаты. Сначала очистите результаты в разделе инструментальных исследований.'))
                    return redirect('examination_management:plan_detail',
                                  kwargs={
                                      'owner_model': 'encounter',
                                      'owner_id': self.object.examination_plan.encounter.id,
                                      'pk': self.object.examination_plan.pk
                                  })
                else:
                    # Если результатов нет, назначение будет удалено автоматически через сигнал
                    messages.success(request, _('Инструментальное исследование и связанное назначение будут удалены'))
            else:
                messages.info(request, _('Связанное назначение не найдено'))
                
        except Exception as e:
            messages.warning(request, _('Ошибка при проверке назначения: {}').format(str(e)))
        
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        context['encounter'] = self.object.examination_plan.encounter
        context['patient'] = self.object.examination_plan.encounter.patient
        context['title'] = _('Удалить инструментальное исследование')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.examination_plan.encounter.id,
                          'pk': self.object.examination_plan.pk
                      })
