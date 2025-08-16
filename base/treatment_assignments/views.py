# treatment_assignments/views.py
import re
import copy
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from itertools import chain
from django.conf import settings
from django.http import JsonResponse


from .models import MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment, InstrumentalProcedureAssignment
from .forms import MedicationAssignmentForm, GeneralTreatmentAssignmentForm, LabTestAssignmentForm, \
    InstrumentalProcedureAssignmentForm
from patients.models import Patient
from departments.models import PatientDepartmentStatus

# Словарь для сопоставления типов из URL с моделями
ASSIGNMENT_MODELS = {
    'medication': MedicationAssignment,
    'general': GeneralTreatmentAssignment,
    'lab': LabTestAssignment,
    'instrumental': InstrumentalProcedureAssignment,
}

# (Вспомогательная функция и CreateViews остаются без изменений)
def get_treatment_assignment_back_url(obj_or_parent_obj):
    parent_obj = None
    if isinstance(obj_or_parent_obj, tuple(ASSIGNMENT_MODELS.values())):
        parent_obj = obj_or_parent_obj.content_object
    else:
        parent_obj = obj_or_parent_obj
    if parent_obj:
        content_type = ContentType.objects.get_for_model(parent_obj)
        if content_type.model == 'patientdepartmentstatus':
            return reverse('departments:patient_history', kwargs={'pk': parent_obj.pk})
    return reverse_lazy('patients:patient_list')



# Универсальная функция для получения queryset с нужными связями
def get_base_queryset(model):
    base_qs = model.objects.all().select_related('patient')
    if model == MedicationAssignment:
        base_qs = base_qs.select_related('medication')
    elif model == LabTestAssignment:
        base_qs = base_qs.select_related('lab_test')
    elif model == InstrumentalProcedureAssignment:
        base_qs = base_qs.select_related('instrumental_procedure')
    # GeneralTreatmentAssignment — без select_related (general_treatment = TextField)
    return base_qs



class BaseAssignmentCreateView(LoginRequiredMixin, CreateView):
    template_name = 'treatment_assignments/form.html'
    assignment_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        model_name = self.kwargs.get('model_name')
        object_id = self.kwargs.get('object_id')
        content_type_model = get_object_or_404(ContentType, model=model_name)
        self.parent_object = get_object_or_404(content_type_model.model_class(), pk=object_id)
        if isinstance(self.parent_object, PatientDepartmentStatus):
            self.patient_object = self.parent_object.patient
        elif isinstance(self.parent_object, Patient):
            self.patient_object = self.parent_object
        else:
            self.patient_object = None

    # --- ИЗМЕНЕНИЕ: Добавлен метод get_initial для автозаполнения даты ---
    def get_initial(self):
        initial = super().get_initial()
        start_date_str = self.request.GET.get('start_date')
        if start_date_str:
            try:
                dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                # Используем USE_TZ из настроек, чтобы корректно обработать часовые пояса
                initial['start_date'] = timezone.make_aware(dt) if settings.USE_TZ else dt
            except (ValueError, TypeError):
                # Игнорируем некорректный формат даты
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        kwargs['content_object'] = self.parent_object
        kwargs['patient_object'] = self.patient_object
        return kwargs

    def form_valid(self, form):
        form.instance.content_type = ContentType.objects.get_for_model(self.parent_object)
        form.instance.object_id = self.parent_object.pk

        # СРАЗУ устанавливаем пациента ДО вызова super().form_valid()
        if self.patient_object:
            form.instance.patient = self.patient_object
        elif hasattr(self.parent_object, 'patient'):
            form.instance.patient = self.parent_object.patient
        else:
            raise ValueError("Не удалось определить пациента для назначения")

        form.instance.assigning_doctor = self.request.user
        start_date = self.request.GET.get('start_date')
        if start_date:
            form.instance.start_date = start_date

        # Сохраняем сразу без вызова super(), чтобы исключить риск повторного обращения к .patient
        obj = form.save(commit=False)
        obj.save()
        form.save_m2m()
        self.object = obj  # важно для дальнейшего выполнения метода

        return super().form_valid(form)

    # --- ИЗМЕНЕНИЕ: Удалена логика для AJAX из form_invalid ---
    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment_type'] = self.assignment_type
        # Используем get_treatment_assignment_back_url для более надежной генерации URL отмены
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.parent_object))
        context['parent_object'] = self.parent_object
        return context

    def get_success_url(self):
        # Приоритет 'next' из GET-параметра для возврата на предыдущую страницу
        return self.request.GET.get('next', self.object.get_absolute_url())


class MedicationAssignmentCreateView(BaseAssignmentCreateView):
    model = MedicationAssignment
    form_class = MedicationAssignmentForm
    assignment_type = 'medication'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создать назначение препарата'
        return context


class GeneralTreatmentAssignmentCreateView(BaseAssignmentCreateView):
    model = GeneralTreatmentAssignment
    form_class = GeneralTreatmentAssignmentForm
    assignment_type = 'general'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создать общее назначение'
        return context


class LabTestAssignmentCreateView(BaseAssignmentCreateView):
    model = LabTestAssignment
    form_class = LabTestAssignmentForm
    assignment_type = 'lab'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создать лабораторное исследование'
        return context


class InstrumentalProcedureAssignmentCreateView(BaseAssignmentCreateView):
    model = InstrumentalProcedureAssignment
    form_class = InstrumentalProcedureAssignmentForm
    assignment_type = 'instrumental'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создать инструментальное исследование'
        return context


class BaseAssignmentActionView:
    """Базовый миксин для Detail, Update, Delete"""

    def get_model_class(self):
        assignment_type = self.kwargs.get('assignment_type')
        return ASSIGNMENT_MODELS.get(assignment_type)

    def get_queryset(self):
        model_class = self.get_model_class()
        if not model_class:
            raise Http404("Неверный тип назначения")
        return model_class.objects.select_related('patient', 'assigning_doctor')


class TreatmentAssignmentDetailView(BaseAssignmentActionView, DetailView):
    template_name = 'treatment_assignments/detail.html'
    context_object_name = 'assignment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment_type'] = self.kwargs.get('assignment_type')
        context['title'] = f"Детали назначения №{self.object.pk}"
        
        # Приоритет: 1) GET параметр next, 2) HTTP_REFERER, 3) fallback URL
        next_url = self.request.GET.get('next')
        if not next_url:
            # Пытаемся получить URL из HTTP_REFERER
            referer = self.request.META.get('HTTP_REFERER')
            if referer:
                # Проверяем, что referer не ведет на внешний сайт
                from django.conf import settings
                if referer.startswith(settings.SITE_URL) if hasattr(settings, 'SITE_URL') else True:
                    next_url = referer
        
        # Если все еще нет next_url, используем fallback
        if not next_url:
            next_url = get_treatment_assignment_back_url(self.object)
        
        context['next_url'] = next_url
        return context


class TreatmentAssignmentUpdateView(BaseAssignmentActionView, UpdateView):
    template_name = 'treatment_assignments/form.html'

    def get_form_class(self):
        assignment_type = self.kwargs.get('assignment_type')
        if assignment_type == 'medication': return MedicationAssignmentForm
        if assignment_type == 'general': return GeneralTreatmentAssignmentForm
        if assignment_type == 'lab': return LabTestAssignmentForm
        if assignment_type == 'instrumental': return InstrumentalProcedureAssignmentForm
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment_type'] = self.kwargs.get('assignment_type')
        context['title'] = 'Редактировать назначение'
        
        # Приоритет: 1) GET параметр next, 2) HTTP_REFERER, 3) fallback URL
        next_url = self.request.GET.get('next')
        if not next_url:
            # Пытаемся получить URL из HTTP_REFERER
            referer = self.request.META.get('HTTP_REFERER')
            if referer:
                # Проверяем, что referer не ведет на внешний сайт
                from django.conf import settings
                if referer.startswith(settings.SITE_URL) if hasattr(settings, 'SITE_URL') else True:
                    next_url = referer
        
        # Если все еще нет next_url, используем fallback
        if not next_url:
            next_url = get_treatment_assignment_back_url(self.object)
        
        context['next_url'] = next_url
        return context

    def get_success_url(self):
        # Приоритет: 1) GET параметр next, 2) HTTP_REFERER, 3) детали назначения
        next_url = self.request.GET.get('next')
        if not next_url:
            # Пытаемся получить URL из HTTP_REFERER
            referer = self.request.META.get('HTTP_REFERER')
            if referer:
                # Проверяем, что referer не ведет на внешний сайт
                from django.conf import settings
                if referer.startswith(settings.SITE_URL) if hasattr(settings, 'SITE_URL') else True:
                    next_url = referer
        
        # Если все еще нет next_url, переходим к деталям назначения
        if not next_url:
            next_url = self.object.get_absolute_url()
        
        return next_url


class TreatmentAssignmentDeleteView(BaseAssignmentActionView, DeleteView):
    template_name = 'treatment_assignments/confirm_delete.html'
    context_object_name = 'assignment'

    def get_success_url(self):
        # Приоритет: 1) GET параметр next, 2) HTTP_REFERER, 3) fallback URL
        next_url = self.request.GET.get('next')
        if not next_url:
            # Пытаемся получить URL из HTTP_REFERER
            referer = self.request.META.get('HTTP_REFERER')
            if referer:
                # Проверяем, что referer не ведет на внешний сайт
                from django.conf import settings
                if referer.startswith(settings.SITE_URL) if hasattr(settings, 'SITE_URL') else True:
                    next_url = referer
        
        # Если все еще нет next_url, используем fallback
        if not next_url:
            next_url = get_treatment_assignment_back_url(self.object)
        
        return next_url


# (DailyTreatmentPlanView и ListView остаются без изменений)
# treatment_assignments/views.py

class DailyTreatmentPlanView(LoginRequiredMixin, View):
    template_name = 'treatment_assignments/daily_plan.html'

    def get(self, request, model_name, object_id, *args, **kwargs):
        content_type = get_object_or_404(ContentType, model=model_name)
        parent_obj = get_object_or_404(content_type.model_class(), pk=object_id)
        patient = parent_obj.patient if isinstance(parent_obj, PatientDepartmentStatus) else parent_obj if isinstance(
            parent_obj, Patient) else None
        if not patient:
            raise Http404("Пациент не определен для данного объекта")

        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if start_date_str and end_date_str:
            start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            if isinstance(parent_obj, PatientDepartmentStatus) and parent_obj.admission_date:
                start_date = parent_obj.admission_date.date()
            else:
                start_date = timezone.localdate()
            end_date = start_date + timedelta(days=13)

        duration_days = (end_date - start_date).days
        next_start_date = end_date + timedelta(days=1)
        prev_start_date = start_date - timedelta(days=duration_days + 1)

        q_active_in_range = Q(start_date__date__lte=end_date) & \
                            (Q(end_date__date__gte=start_date) | Q(end_date__isnull=True)) & \
                            ~Q(status='paused')
        med_qs = MedicationAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related(
            'medication', 'dosing_rule')
        gen_qs = GeneralTreatmentAssignment.objects.all().select_related('patient')
        lab_qs = LabTestAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related('lab_test')
        inst_qs = InstrumentalProcedureAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related(
            'instrumental_procedure')

        all_assignments = list(chain(med_qs, gen_qs, lab_qs, inst_qs))
        daily_plan_dict = {
            start_date + timedelta(days=i): {'medications': [], 'general_treatments': [], 'lab_tests': [],
                                             'instrumental_procedures': []} for i in
            range((end_date - start_date).days + 1)}

        # --- НАЧАЛО ИСПРАВЛЕННОЙ ЛОГИКИ ЦИКЛА ---
        for assignment in all_assignments:
            # ПРАВИЛО 1: Отдельная логика для инструментальных исследований
            if isinstance(assignment, InstrumentalProcedureAssignment):
                assignment_start_date = assignment.start_date.date()
                if start_date <= assignment_start_date <= end_date:
                    assignment.display_type = 'order'
                    daily_plan_dict[assignment_start_date]['instrumental_procedures'].append(assignment)
                if assignment.status == 'completed' and assignment.end_date:
                    assignment_end_date = assignment.end_date.date()
                    if start_date <= assignment_end_date <= end_date and assignment_end_date != assignment_start_date:
                        result_marker = copy.copy(assignment)
                        result_marker.display_type = 'result'
                        daily_plan_dict[assignment_end_date]['instrumental_procedures'].append(result_marker)

            # --- НАЧАЛО НОВОГО БЛОКА ---
            # ПРАВИЛО 2: Такая же логика для лабораторных анализов
            elif isinstance(assignment, LabTestAssignment):
                assignment_start_date = assignment.start_date.date()
                # Показываем назначение ТОЛЬКО в день его создания
                if start_date <= assignment_start_date <= end_date:
                    assignment.display_type = 'order'
                    daily_plan_dict[assignment_start_date]['lab_tests'].append(assignment)

                # Если анализ выполнен, добавляем отметку о результате
                if assignment.status == 'completed' and assignment.end_date:
                    assignment_end_date = assignment.end_date.date()
                    if start_date <= assignment_end_date <= end_date and assignment_end_date != assignment_start_date:
                        result_marker = copy.copy(assignment)
                        result_marker.display_type = 'result'
                        daily_plan_dict[assignment_end_date]['lab_tests'].append(result_marker)
            # --- КОНЕЦ НОВОГО БЛОКА ---

            # ПРАВИЛО 3: Общая логика для всех остальных назначений (медикаменты, общие)
            else:
                assignment_start = assignment.start_date.date()
                assignment_end = None

                if isinstance(assignment, MedicationAssignment) and assignment.duration_days:
                    assignment_end = assignment_start + timedelta(days=assignment.duration_days - 1)

                if not assignment_end:
                    assignment_end = assignment.end_date.date() if assignment.end_date else end_date

                current_date = max(assignment_start, start_date)
                while current_date <= min(assignment_end, end_date):
                    if isinstance(assignment, MedicationAssignment):
                        daily_plan_dict[current_date]['medications'].append(assignment)
                    elif isinstance(assignment, GeneralTreatmentAssignment):
                        daily_plan_dict[current_date]['general_treatments'].append(assignment)
                    current_date += timedelta(days=1)
        # --- КОНЕЦ ИСПРАВЛЕННОЙ ЛОГИКИ ЦИКЛА ---

        daily_plan_list = sorted(daily_plan_dict.items())

        context = {
            'patient': patient, 'parent_obj': parent_obj, 'parent_model_name': model_name,
            'daily_plan_list': daily_plan_list, 'start_date': start_date, 'end_date': end_date,
            'title': f'Лист назначений для {patient.full_name}',
            'next_url': get_treatment_assignment_back_url(parent_obj),
            'today': timezone.localdate(),
            'next_start_date': next_start_date.strftime('%Y-%m-%d'),
            'next_end_date': (next_start_date + timedelta(days=duration_days)).strftime('%Y-%m-%d'),
            'prev_start_date': prev_start_date.strftime('%Y-%m-%d'),
            'prev_end_date': (prev_start_date + timedelta(days=duration_days)).strftime('%Y-%m-%d'),
        }
        return render(request, self.template_name, context)


class TreatmentAssignmentListView(LoginRequiredMixin, ListView):
    template_name = 'treatment_assignments/list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        med_qs = get_base_queryset(MedicationAssignment)
        gen_qs = get_base_queryset(GeneralTreatmentAssignment)
        lab_qs = get_base_queryset(LabTestAssignment)
        inst_qs = get_base_queryset(InstrumentalProcedureAssignment)
        all_assignments = sorted(chain(med_qs, gen_qs, lab_qs, inst_qs), key=lambda x: x.start_date, reverse=True)
        return all_assignments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Все назначения'
        return context
