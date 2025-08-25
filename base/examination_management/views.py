from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, DeleteView, DetailView
)
from django.urls import reverse, reverse_lazy
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views import View

from .models import ExaminationPlan, ExaminationLabTest, ExaminationInstrumental
from .forms import ExaminationPlanForm, ExaminationLabTestForm, ExaminationInstrumentalForm, ExaminationLabTestWithScheduleForm, ExaminationInstrumentalWithScheduleForm
from .status_forms import RejectionForm, PauseForm, CompletionForm

# Импорты для просмотра результатов
from lab_tests.models import LabTestResult
from instrumental_procedures.models import InstrumentalProcedureResult
from document_signatures.models import DocumentSignature

# Импортируем сервис для создания планов обследования
from .services import ExaminationPlanService, ExaminationStatusService

# Импортируем миксины для перенаправления на настройку расписания
from clinical_scheduling.mixins import LabTestScheduleRedirectMixin, ProcedureScheduleRedirectMixin
from clinical_scheduling.services import ClinicalSchedulingService

# Импортируем Encounter для специальных URL
try:
    from encounters.models import Encounter
except ImportError:
    Encounter = None

# Импорты treatment_assignments удалены - больше не нужны


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


class ExaminationPlanQuickCreateView(LoginRequiredMixin, View):
    """
    Быстрое создание плана обследования для Encounter:
    - если планов нет — создается "Основной" со стандартным описанием
    - если планы есть — перенаправляем на список планов
    """
    def get(self, request, *args, **kwargs):
        from encounters.models import Encounter
        encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
        plans_qs = ExaminationPlanService.get_examination_plans(encounter)
        if plans_qs.exists():
            return redirect('examination_management:examination_plan_list', encounter_pk=encounter.pk)
        # создаем основной план
        plan = ExaminationPlanService.create_examination_plan(
            owner=encounter,
            name='Основной',
            description='Стандартный план обследования',
            priority='normal',
            is_active=True,
            created_by=request.user,
        )
        return redirect('examination_management:examination_plan_detail', encounter_pk=encounter.pk, pk=plan.pk)


class ExaminationPlanListView(LoginRequiredMixin, OwnerContextMixin, ListView):
    """
    Список планов обследования для владельца
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_list.html'
    context_object_name = 'examination_plans'
    
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
        # Используем сервис для получения планов
        return ExaminationPlanService.get_examination_plans(self.owner).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
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


class ExaminationPlanCreateView(LoginRequiredMixin, OwnerContextMixin, CreateView):
    """
    Создание плана обследования
    """
    model = ExaminationPlan
    form_class = ExaminationPlanForm
    template_name = 'examination_management/plan_form.html'
    
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
    
    def get_patient_from_owner(self, owner):
        """
        Получает пациента из владельца
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Передаем owner в форму для валидации
        kwargs['owner'] = self.owner
        
        # Устанавливаем initial значения для owner_type и owner_id
        owner_model_name = self.owner._meta.model_name
        if owner_model_name == 'patientdepartmentstatus':
            kwargs['owner_type'] = 'department'
            kwargs['owner_id'] = self.owner.pk
        elif owner_model_name == 'encounter':
            kwargs['owner_type'] = 'encounter'
            kwargs['owner_id'] = self.owner.pk
        
        return kwargs
    
    def form_valid(self, form):
        # Создаем план обследования через сервис
        examination_plan = ExaminationPlanService.create_examination_plan(
            owner=self.owner,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
            priority=form.cleaned_data['priority'],
            is_active=form.cleaned_data['is_active'],
            created_by=self.request.user
        )
        
        messages.success(self.request, _('План обследования успешно создан'))
        return redirect('examination_management:plan_detail',
                       owner_model=self.kwargs['owner_model'],
                       owner_id=self.kwargs['owner_id'],
                       pk=examination_plan.pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.owner
        context['owner_model'] = self.owner._meta.model_name
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



class ExaminationPlanDetailView(LoginRequiredMixin, DetailView):
    """
    Детальный просмотр плана обследования
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_detail.html'
    context_object_name = 'examination_plan'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            from encounters.models import Encounter
            self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            self.owner = self.encounter
            self.owner_model = 'encounter'
            self.patient = self.encounter.patient
        return super().dispatch(request, *args, **kwargs)
    
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
    Удаление плана обследования (мягкое удаление)
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_confirm_delete.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            from encounters.models import Encounter
            self.encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            self.owner = self.encounter
            self.owner_model = 'encounter'
            self.patient = self.encounter.patient
        return super().dispatch(request, *args, **kwargs)
    
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
        
        context['title'] = _('Отменить план обследования')
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Переопределяем метод delete для использования soft delete
        """
        self.object = self.get_object()
        
        # Сначала отменяем все активные лабораторные исследования в плане
        for lab_test in self.object.lab_tests.filter(status='active'):
            lab_test.cancel(
                reason="План обследования отменен",
                cancelled_by=request.user
            )
        
        # Отменяем все активные инструментальные исследования в плане
        for instrumental in self.object.instrumental_procedures.filter(status='active'):
            instrumental.cancel(
                reason="План обследования отменен",
                cancelled_by=request.user
            )
        
        # Отменяем сам план обследования
        self.object.cancel(
            reason="Отменено через веб-интерфейс",
            cancelled_by=request.user
        )
        
        messages.success(request, _('План обследования и все исследования успешно отменены'))
        return redirect(self.get_success_url())
    
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
    Добавление лабораторного исследования в план обследования с настройкой расписания
    """
    model = ExaminationLabTest
    form_class = ExaminationLabTestWithScheduleForm
    template_name = 'examination_management/lab_test_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.examination_plan = get_object_or_404(ExaminationPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.examination_plan = self.examination_plan
        # Сохраняем значение lab_test из формы
        form.instance.lab_test = form.cleaned_data['lab_test']
        
        # Сохраняем объект
        response = super().form_valid(form)
        
        # Создаем запись результата в lab_tests для заполнения врачом/лаборантом
        try:
            from .services import ExaminationIntegrationService
            result = ExaminationIntegrationService.create_lab_test_result(
                form.instance, self.request.user
            )
            if result:
                messages.success(self.request, _('Лабораторное исследование добавлено в план. Запись для заполнения результата создана.'))
            else:
                messages.warning(self.request, _('Исследование добавлено в план, но возникла ошибка при создании записи для результата.'))
        except Exception as e:
            messages.warning(self.request, _('Исследование добавлено в план, но возникла ошибка при создании записи для результата: {}').format(str(e)))
        
        # Создаем расписание, если оно включено
        if form.cleaned_data.get('enable_schedule'):
            try:
                ExaminationStatusService.create_schedule_for_assignment(
                    examination_item=form.instance,
                    user=self.request.user,
                    start_date=form.cleaned_data['start_date'],
                    first_time=form.cleaned_data['first_time'],
                    times_per_day=form.cleaned_data['times_per_day'],
                    duration_days=form.cleaned_data['duration_days']
                )
                messages.success(self.request, _('Расписание успешно создано.'))
            except Exception as e:
                messages.warning(self.request, _('Возникла ошибка при создании расписания: {}').format(str(e)))
        
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




class ExaminationLabTestDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление лабораторного исследования из плана обследования (мягкое удаление)
    """
    model = ExaminationLabTest
    template_name = 'examination_management/lab_test_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        context['encounter'] = self.object.examination_plan.encounter
        context['patient'] = self.object.examination_plan.encounter.patient
        context['title'] = _('Отменить лабораторное исследование')
        
        # Проверяем возможность удаления
        context['can_be_deleted'] = self.object.can_be_deleted()
        
        # Дополнительная проверка статуса
        if hasattr(self.object, 'status') and self.object.status == 'completed':
            context['warning_message'] = _('Удаление невозможно - исследование выполнено. Удалите результат в разделе лабораторных исследований.')
            context['can_be_deleted'] = False
        elif not context['can_be_deleted']:
            context['warning_message'] = _('Удаление невозможно - есть подписанное заключение. Удалите заключение в разделе лабораторных исследований.')
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Переопределяем метод delete для использования soft delete
        """
        self.object = self.get_object()
        
        # Дополнительная защита: проверяем статус
        if hasattr(self.object, 'status') and self.object.status == 'completed':
            messages.error(request, _('Удаление невозможно - исследование выполнено. Удалите результат в разделе лабораторных исследований.'))
            return redirect(self.get_success_url())
        
        # Проверяем, можно ли удалить назначение
        if not self.object.can_be_deleted():
            messages.error(request, _('Удаление невозможно - есть подписанное заключение. Удалите заключение в разделе лабораторных исследований.'))
            return redirect(self.get_success_url())
        
        # Используем soft delete вместо физического удаления
        self.object.cancel(
            reason="Отменено через веб-интерфейс",
            cancelled_by=request.user
        )
        
        messages.success(request, _('Лабораторное исследование успешно отменено'))
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.examination_plan.encounter.id,
                          'pk': self.object.examination_plan.pk
                      })


class ExaminationInstrumentalCreateView(LoginRequiredMixin, CreateView):
    """
    Добавление инструментального исследования в план обследования с настройкой расписания
    """
    model = ExaminationInstrumental
    form_class = ExaminationInstrumentalWithScheduleForm
    template_name = 'examination_management/instrumental_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.examination_plan = get_object_or_404(ExaminationPlan, pk=self.kwargs['plan_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.examination_plan = self.examination_plan
        # Сохраняем значение instrumental_procedure из формы
        form.instance.instrumental_procedure = form.cleaned_data['instrumental_procedure']
        
        # Сохраняем объект
        response = super().form_valid(form)
        
        # Создаем запись результата в instrumental_procedures для заполнения врачом/лаборантом
        try:
            from .services import ExaminationIntegrationService
            result = ExaminationIntegrationService.create_instrumental_procedure_result(
                form.instance, self.request.user
            )
            if result:
                messages.success(self.request, _('Инструментальное исследование добавлено в план. Запись для заполнения результата создана.'))
            else:
                messages.warning(self.request, _('Исследование добавлено в план, но возникла ошибка при создании записи для результата.'))
        except Exception as e:
            messages.warning(self.request, _('Исследование добавлено в план, но возникла ошибка при создании записи для результата: {}').format(str(e)))
        
        # Создаем расписание, если оно включено
        if form.cleaned_data.get('enable_schedule'):
            try:
                ExaminationStatusService.create_schedule_for_assignment(
                    examination_item=form.instance,
                    user=self.request.user,
                    start_date=form.cleaned_data['start_date'],
                    first_time=form.cleaned_data['first_time'],
                    times_per_day=form.cleaned_data['times_per_day'],
                    duration_days=form.cleaned_data['duration_days']
                )
                messages.success(self.request, _('Расписание успешно создано.'))
            except Exception as e:
                messages.warning(self.request, _('Возникла ошибка при создании расписания: {}').format(str(e)))
        
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





class ExaminationInstrumentalDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление инструментального исследования из плана обследования (мягкое удаление)
    """
    model = ExaminationInstrumental
    template_name = 'examination_management/instrumental_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.object.examination_plan
        context['encounter'] = self.object.examination_plan.encounter
        context['patient'] = self.object.examination_plan.encounter.patient
        context['title'] = _('Отменить инструментальное исследование')
        
        # Проверяем возможность удаления
        context['can_be_deleted'] = self.object.can_be_deleted()
        
        # Дополнительная проверка статуса
        if hasattr(self.object, 'status') and self.object.status == 'completed':
            context['warning_message'] = _('Удаление невозможно - исследование выполнено. Удалите результат в разделе инструментальных исследований.')
            context['can_be_deleted'] = False
        elif not context['can_be_deleted']:
            context['warning_message'] = _('Удаление невозможно - есть подписанное заключение. Удалите заключение в разделе инструментальных исследований.')
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Переопределяем метод delete для использования soft delete
        """
        self.object = self.get_object()
        
        # Дополнительная защита: проверяем статус
        if hasattr(self.object, 'status') and self.object.status == 'completed':
            messages.error(request, _('Удаление невозможно - исследование выполнено. Удалите результат в разделе инструментальных исследований.'))
            return redirect(self.get_success_url())
        
        # Проверяем, можно ли удалить назначение
        if not self.object.can_be_deleted():
            messages.error(request, _('Удаление невозможно - есть подписанное заключение. Удалите заключение в разделе инструментальных исследований.'))
            return redirect(self.get_success_url())
        
        # Используем soft delete вместо физического удаления
        self.object.cancel(
            reason="Отменено через веб-интерфейс",
            cancelled_by=request.user
        )
        
        messages.success(request, _('Инструментальное исследование успешно отменено'))
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.examination_plan.encounter.id,
                          'pk': self.object.examination_plan.pk
                      })


# ============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ УПРАВЛЕНИЯ СТАТУСАМИ НАЗНАЧЕНИЙ
# ============================================================================

class ExaminationLabTestCompleteView(LoginRequiredMixin, View):
    """Отметить лабораторное исследование как выполненное"""
    
    def post(self, request, *args, **kwargs):
        lab_test = get_object_or_404(ExaminationLabTest, pk=self.kwargs['pk'])
        
        try:
            # Обновляем статус в examination_management
            lab_test.status = 'completed'
            lab_test.completed_at = timezone.now()
            lab_test.completed_by = request.user
            lab_test.save()
            
            # Обновляем статус в clinical_scheduling
            ExaminationStatusService.update_assignment_status(
                lab_test, 'completed', request.user, 'Отмечено как выполненное'
            )
            
            messages.success(request, _('Лабораторное исследование отмечено как выполненное.'))
        except Exception as e:
            messages.error(request, _('Ошибка при обновлении статуса: {}').format(str(e)))
        
        # Перенаправляем обратно на детальную страницу плана
        return redirect('examination_management:plan_detail',
                       owner_model=lab_test.examination_plan.get_owner_model_name(),
                       owner_id=lab_test.examination_plan.get_owner_id(),
                       pk=lab_test.examination_plan.pk)


class ExaminationLabTestRejectView(LoginRequiredMixin, View):
    """Отклонить лабораторное исследование"""
    
    def get(self, request, *args, **kwargs):
        lab_test = get_object_or_404(ExaminationLabTest, pk=self.kwargs['pk'])
        form = RejectionForm()
        return render(request, 'examination_management/status_forms/reject_form.html', {
            'form': form,
            'examination_item': lab_test,
            'item_type': 'lab_test',
            'title': _('Отклонить лабораторное исследование')
        })
    
    def post(self, request, *args, **kwargs):
        lab_test = get_object_or_404(ExaminationLabTest, pk=self.kwargs['pk'])
        form = RejectionForm(request.POST)
        
        if form.is_valid():
            rejection_reason = form.cleaned_data['rejection_reason']
            
            try:
                # Обновляем статус в examination_management
                lab_test.status = 'rejected'
                lab_test.cancelled_at = timezone.now()
                lab_test.cancelled_by = request.user
                lab_test.cancellation_reason = rejection_reason
                lab_test.save()
                
                # Обновляем статус в clinical_scheduling
                ExaminationStatusService.update_assignment_status(
                    lab_test, 'rejected', request.user, rejection_reason
                )
                
                messages.success(request, _('Лабораторное исследование отклонено.'))
                return redirect('examination_management:plan_detail',
                               owner_model=lab_test.examination_plan.get_owner_model_name(),
                               owner_id=lab_test.examination_plan.get_owner_id(),
                               pk=lab_test.examination_plan.pk)
            except Exception as e:
                messages.error(request, _('Ошибка при отклонении: {}').format(str(e)))
        else:
            messages.error(request, _('Пожалуйста, исправьте ошибки в форме.'))
        
        return render(request, 'examination_management/status_forms/reject_form.html', {
            'form': form,
            'examination_item': lab_test,
            'item_type': 'lab_test',
            'title': _('Отклонить лабораторное исследование')
        })


class ExaminationLabTestPauseView(LoginRequiredMixin, View):
    """Приостановить лабораторное исследование"""
    
    def get(self, request, *args, **kwargs):
        lab_test = get_object_or_404(ExaminationLabTest, pk=self.kwargs['pk'])
        form = PauseForm()
        return render(request, 'examination_management/status_forms/pause_form.html', {
            'form': form,
            'examination_item': lab_test,
            'item_type': 'lab_test',
            'title': _('Приостановить лабораторное исследование')
        })
    
    def post(self, request, *args, **kwargs):
        lab_test = get_object_or_404(ExaminationLabTest, pk=self.kwargs['pk'])
        form = PauseForm(request.POST)
        
        if form.is_valid():
            pause_reason = form.cleaned_data['pause_reason']
            
            try:
                # Обновляем статус в examination_management
                lab_test.status = 'paused'
                lab_test.paused_at = timezone.now()
                lab_test.paused_by = request.user
                lab_test.pause_reason = pause_reason
                lab_test.save()
                
                # Обновляем статус в clinical_scheduling
                ExaminationStatusService.update_assignment_status(
                    lab_test, 'skipped', request.user, pause_reason
                )
                
                messages.success(request, _('Лабораторное исследование приостановлено.'))
                return redirect('examination_management:plan_detail',
                               owner_model=lab_test.examination_plan.get_owner_model_name(),
                               owner_id=lab_test.examination_plan.get_owner_id(),
                               pk=lab_test.examination_plan.pk)
            except Exception as e:
                messages.error(request, _('Ошибка при приостановке: {}').format(str(e)))
        else:
            messages.error(request, _('Пожалуйста, исправьте ошибки в форме.'))
        
        return render(request, 'examination_management/status_forms/pause_form.html', {
            'form': form,
            'examination_item': lab_test,
            'item_type': 'lab_test',
            'title': _('Приостановить лабораторное исследование')
        })


class ExaminationInstrumentalCompleteView(LoginRequiredMixin, View):
    """Отметить инструментальное исследование как выполненное"""
    
    def post(self, request, *args, **kwargs):
        instrumental = get_object_or_404(ExaminationInstrumental, pk=self.kwargs['pk'])
        
        try:
            # Обновляем статус в examination_management
            instrumental.status = 'completed'
            instrumental.completed_at = timezone.now()
            instrumental.completed_by = request.user
            instrumental.save()
            
            # Обновляем статус в clinical_scheduling
            ExaminationStatusService.update_assignment_status(
                instrumental, 'completed', request.user, 'Отмечено как выполненное'
            )
            
            messages.success(request, _('Инструментальное исследование отмечено как выполненное.'))
        except Exception as e:
            messages.error(request, _('Ошибка при обновлении статуса: {}').format(str(e)))
        
        return redirect('examination_management:plan_detail',
                       owner_model=instrumental.examination_plan.get_owner_model_name(),
                       owner_id=instrumental.examination_plan.get_owner_id(),
                       pk=instrumental.examination_plan.pk)


class ExaminationInstrumentalRejectView(LoginRequiredMixin, View):
    """Отклонить инструментальное исследование"""
    
    def get(self, request, *args, **kwargs):
        instrumental = get_object_or_404(ExaminationInstrumental, pk=self.kwargs['pk'])
        form = RejectionForm()
        return render(request, 'examination_management/status_forms/reject_form.html', {
            'form': form,
            'examination_item': instrumental,
            'item_type': 'instrumental',
            'title': _('Отклонить инструментальное исследование')
        })
    
    def post(self, request, *args, **kwargs):
        instrumental = get_object_or_404(ExaminationInstrumental, pk=self.kwargs['pk'])
        form = RejectionForm(request.POST)
        
        if form.is_valid():
            rejection_reason = form.cleaned_data['rejection_reason']
            
            try:
                # Обновляем статус в examination_management
                instrumental.status = 'rejected'
                instrumental.cancelled_at = timezone.now()
                instrumental.cancelled_by = request.user
                instrumental.cancellation_reason = rejection_reason
                instrumental.save()
                
                # Обновляем статус в clinical_scheduling
                ExaminationStatusService.update_assignment_status(
                    instrumental, 'rejected', request.user, rejection_reason
                )
                
                messages.success(request, _('Инструментальное исследование отклонено.'))
                return redirect('examination_management:plan_detail',
                               owner_model=instrumental.examination_plan.get_owner_model_name(),
                               owner_id=instrumental.examination_plan.get_owner_id(),
                               pk=instrumental.examination_plan.pk)
            except Exception as e:
                messages.error(request, _('Ошибка при отклонении: {}').format(str(e)))
        else:
            messages.error(request, _('Пожалуйста, исправьте ошибки в форме.'))
        
        return render(request, 'examination_management/status_forms/reject_form.html', {
            'form': form,
            'examination_item': instrumental,
            'item_type': 'instrumental',
            'title': _('Отклонить инструментальное исследование')
        })


class ExaminationInstrumentalPauseView(LoginRequiredMixin, View):
    """Приостановить инструментальное исследование"""
    
    def get(self, request, *args, **kwargs):
        instrumental = get_object_or_404(ExaminationInstrumental, pk=self.kwargs['pk'])
        form = PauseForm()
        return render(request, 'examination_management/status_forms/pause_form.html', {
            'form': form,
            'examination_item': instrumental,
            'item_type': 'instrumental',
            'title': _('Приостановить инструментальное исследование')
        })
    
    def post(self, request, *args, **kwargs):
        instrumental = get_object_or_404(ExaminationInstrumental, pk=self.kwargs['pk'])
        form = PauseForm(request.POST)
        
        if form.is_valid():
            pause_reason = form.cleaned_data['pause_reason']
            
            try:
                # Обновляем статус в examination_management
                instrumental.status = 'paused'
                instrumental.paused_at = timezone.now()
                instrumental.paused_by = request.user
                instrumental.pause_reason = pause_reason
                instrumental.save()
                
                # Обновляем статус в clinical_scheduling
                ExaminationStatusService.update_assignment_status(
                    instrumental, 'skipped', request.user, pause_reason
                )
                
                messages.success(request, _('Инструментальное исследование приостановлено.'))
                return redirect('examination_management:plan_detail',
                               owner_model=instrumental.examination_plan.get_owner_model_name(),
                               owner_id=instrumental.examination_plan.get_owner_id(),
                               pk=instrumental.examination_plan.pk)
            except Exception as e:
                messages.error(request, _('Ошибка при приостановке: {}').format(str(e)))
        else:
            messages.error(request, _('Пожалуйста, исправьте ошибки в форме.'))
        
        return render(request, 'examination_management/status_forms/pause_form.html', {
            'form': form,
            'examination_item': instrumental,
            'item_type': 'instrumental',
            'title': _('Приостановить инструментальное исследование')
        })


class LabTestResultView(LoginRequiredMixin, DetailView):
    """
    Представление для просмотра результатов лабораторного исследования
    Только для чтения, без возможности редактирования
    """
    model = ExaminationLabTest
    template_name = 'examination_management/lab_test_result_view.html'
    context_object_name = 'lab_test'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lab_test = self.get_object()
        
        # Получаем план обследования
        examination_plan = lab_test.examination_plan
        context['examination_plan'] = examination_plan
        
        # Получаем пациента
        context['patient'] = examination_plan.get_patient()
        
        # Получаем encounter
        if examination_plan.encounter:
            context['encounter'] = examination_plan.encounter
        else:
            # Если нет прямого encounter, ищем через patient_department_status
            context['encounter'] = None
            if examination_plan.patient_department_status:
                # Создаем фиктивный encounter для отображения
                from encounters.models import Encounter
                context['encounter'] = Encounter(
                    patient=examination_plan.patient_department_status.patient,
                    date_start=examination_plan.patient_department_status.admission_date
                )
        
        # Получаем результат исследования
        try:
            result = LabTestResult.objects.filter(
                examination_plan=examination_plan,
                procedure_definition=lab_test.lab_test
            ).first()
            context['result'] = result
        except Exception:
            context['result'] = None
        
                    # Получаем подписи
            try:
                if result:
                    signatures = DocumentSignature.objects.filter(
                        content_type__model='labtestresult',
                        object_id=result.pk
                    ).select_related('actual_signer', 'required_signer')
                    context['signatures'] = signatures
                else:
                    context['signatures'] = []
            except Exception:
                context['signatures'] = []
        
        return context


class InstrumentalResultView(LoginRequiredMixin, DetailView):
    """
    Представление для просмотра результатов инструментального исследования
    Только для чтения, без возможности редактирования
    """
    model = ExaminationInstrumental
    template_name = 'examination_management/instrumental_result_view.html'
    context_object_name = 'instrumental'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instrumental = self.get_object()
        
        # Получаем план обследования
        examination_plan = instrumental.examination_plan
        context['examination_plan'] = examination_plan
        
        # Получаем пациента
        context['patient'] = examination_plan.get_patient()
        
        # Получаем encounter
        if examination_plan.encounter:
            context['encounter'] = examination_plan.encounter
        else:
            # Если нет прямого encounter, ищем через patient_department_status
            context['encounter'] = None
            if examination_plan.patient_department_status:
                # Создаем фиктивный encounter для отображения
                from encounters.models import Encounter
                context['encounter'] = Encounter(
                    patient=examination_plan.patient_department_status.patient,
                    date_start=examination_plan.patient_department_status.admission_date
                )
        
        # Получаем результат исследования
        try:
            result = InstrumentalProcedureResult.objects.filter(
                examination_plan=examination_plan,
                procedure_definition=instrumental.instrumental_procedure
            ).first()
            context['result'] = result
        except Exception:
            context['result'] = None
        
                    # Получаем подписи
            try:
                if result:
                    signatures = DocumentSignature.objects.filter(
                        content_type__model='instrumentalprocedureresult',
                        object_id=result.pk
                    ).select_related('actual_signer', 'required_signer')
                    context['signatures'] = signatures
                else:
                    context['signatures'] = []
            except Exception:
                context['signatures'] = []
        
        return context
