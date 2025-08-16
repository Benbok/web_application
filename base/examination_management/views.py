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
    """
    
    def get_owner(self):
        """
        Получает объект-владелец из URL параметров
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
        """
        if hasattr(owner, 'patient'):
            return owner.patient
        elif hasattr(owner, 'get_patient'):
            return owner.get_patient()
        return None


class ExaminationPlanListView(LoginRequiredMixin, OwnerContextMixin, ListView):
    """
    Список планов обследования для владельца
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_list.html'
    context_object_name = 'examination_plans'
    
    def get_queryset(self):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            return ExaminationPlan.objects.filter(encounter=encounter).order_by('-created_at')
        else:
            owner = self.get_owner()
            return ExaminationPlan.objects.filter(encounter=owner).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            context['owner'] = encounter
            context['owner_model'] = 'encounter'
            context['patient'] = encounter.patient
        else:
            context['owner'] = self.get_owner()
            context['owner_model'] = self.kwargs.get('owner_model')
            context['patient'] = self.get_patient_from_owner(context['owner'])
        context['title'] = _('Планы обследования')
        return context


class ExaminationPlanCreateView(LoginRequiredMixin, OwnerContextMixin, CreateView):
    """
    Создание плана обследования
    """
    model = ExaminationPlan
    form_class = ExaminationPlanForm
    template_name = 'examination_management/plan_form.html'
    
    def form_valid(self, form):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            form.instance.encounter = encounter
        else:
            owner = self.get_owner()
            form.instance.encounter = owner
        response = super().form_valid(form)
        messages.success(self.request, _('План обследования успешно создан'))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            encounter = get_object_or_404(Encounter, pk=self.kwargs['encounter_pk'])
            context['owner'] = encounter
            context['owner_model'] = 'encounter'
            context['patient'] = encounter.patient
        else:
            context['owner'] = self.get_owner()
            context['owner_model'] = self.kwargs.get('owner_model')
            context['patient'] = self.get_patient_from_owner(context['owner'])
        context['title'] = _('Создать план обследования')
        return context
    
    def get_success_url(self):
        # Проверяем, используем ли мы специальный URL для encounters
        if 'encounter_pk' in self.kwargs:
            return reverse('examination_management:examination_plan_detail',
                          kwargs={
                              'encounter_pk': self.kwargs['encounter_pk'],
                              'pk': self.object.pk
                          })
        else:
            return reverse('examination_management:plan_detail',
                          kwargs={
                              'owner_model': self.kwargs.get('owner_model'),
                              'owner_id': self.kwargs.get('owner_id'),
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
        context['owner'] = self.object.encounter
        context['owner_model'] = 'encounter'
        context['patient'] = self.object.encounter.patient
        context['title'] = _('Редактировать план обследования')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.encounter.id,
                          'pk': self.object.pk
                      })


class ExaminationPlanDetailView(LoginRequiredMixin, DetailView):
    """
    Детальный просмотр плана обследования
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_detail.html'
    context_object_name = 'examination_plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['encounter'] = self.object.encounter
        context['patient'] = self.object.encounter.patient
        return context


class ExaminationPlanDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление плана обследования
    """
    model = ExaminationPlan
    template_name = 'examination_management/plan_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner'] = self.object.encounter
        context['owner_model'] = 'encounter'
        context['patient'] = self.object.encounter.patient
        context['title'] = _('Удалить план обследования')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_list',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.object.encounter.id
                      })


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
        
        # Автоматически создаем назначение для врача-лаборанта
        try:
            LabTestAssignment.objects.create(
                content_type=ContentType.objects.get_for_model(form.instance),
                object_id=form.instance.pk,
                patient=self.examination_plan.encounter.patient,
                assigning_doctor=self.request.user,
                start_date=timezone.now(),
                lab_test=form.instance.lab_test,
                notes=form.instance.instructions
            )
            messages.success(self.request, _('Лабораторное исследование успешно добавлено в план и назначено для выполнения'))
        except Exception as e:
            messages.warning(self.request, _('Исследование добавлено в план, но назначение не создано: {}').format(str(e)))
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.examination_plan
        context['encounter'] = self.examination_plan.encounter
        context['patient'] = self.examination_plan.encounter.patient
        context['title'] = _('Добавить лабораторное исследование')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.examination_plan.encounter.id,
                          'pk': self.examination_plan.pk
                      })


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
                    # Если результатов нет, удаляем назначение
                    assignment.delete()
                    messages.success(request, _('Назначение лабораторного исследования успешно удалено'))
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
        
        # Автоматически создаем назначение для врача-лаборанта
        try:
            InstrumentalProcedureAssignment.objects.create(
                content_type=ContentType.objects.get_for_model(form.instance),
                object_id=form.instance.pk,
                patient=self.examination_plan.encounter.patient,
                assigning_doctor=self.request.user,
                start_date=timezone.now(),
                instrumental_procedure=form.instance.instrumental_procedure,
                notes=form.instance.instructions
            )
            messages.success(self.request, _('Инструментальное исследование успешно добавлено в план и назначено для выполнения'))
        except Exception as e:
            messages.warning(self.request, _('Исследование добавлено в план, но назначение не создано: {}').format(str(e)))
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['examination_plan'] = self.examination_plan
        context['encounter'] = self.examination_plan.encounter
        context['patient'] = self.examination_plan.encounter.patient
        context['title'] = _('Добавить инструментальное исследование')
        return context
    
    def get_success_url(self):
        return reverse('examination_management:plan_detail',
                      kwargs={
                          'owner_model': 'encounter',
                          'owner_id': self.examination_plan.encounter.id,
                          'pk': self.examination_plan.pk
                      })


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
                    # Если результатов нет, удаляем назначение
                    assignment.delete()
                    messages.success(request, _('Назначение инструментального исследования успешно удалено'))
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
