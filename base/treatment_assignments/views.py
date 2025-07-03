# treatment_assignments/views.py
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from itertools import chain

from .models import MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment, InstrumentalProcedureAssignment
from .forms import MedicationAssignmentForm, GeneralTreatmentAssignmentForm, LabTestAssignmentForm, \
    InstrumentalProcedureAssignmentForm
from patients.models import Patient
from departments.models import PatientDepartmentStatus


# --- Вспомогательные функции ---

def get_treatment_assignment_back_url(obj_or_parent_obj):
    """Определяет URL для кнопки "Назад"."""
    parent_obj = None
    if isinstance(obj_or_parent_obj, (MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment,
                                      InstrumentalProcedureAssignment)):
        parent_obj = obj_or_parent_obj.content_object
    else:
        parent_obj = obj_or_parent_obj

    if parent_obj:
        content_type = ContentType.objects.get_for_model(parent_obj)
        if content_type.model == 'patientdepartmentstatus':
            return reverse('departments:patient_history', kwargs={'pk': parent_obj.pk})

    # URL по умолчанию, если ничего не найдено
    return reverse_lazy('patients:patient_list')


# --- Основные CRUD View ---

class BaseAssignmentCreateView(LoginRequiredMixin, CreateView):
    """Базовый класс для создания всех типов назначений."""
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        kwargs['content_object'] = self.parent_object
        kwargs['patient_object'] = self.patient_object
        return kwargs

    def form_valid(self, form):
        form.instance.content_type = ContentType.objects.get_for_model(self.parent_object)
        form.instance.object_id = self.parent_object.pk
        if not form.instance.patient and self.patient_object:
            form.instance.patient = self.patient_object
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment_type'] = self.assignment_type
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.parent_object))
        context['parent_object'] = self.parent_object
        return context

    def get_success_url(self):
        return reverse('treatment_assignments:assignment_detail', kwargs={'pk': self.object.pk})


class MedicationAssignmentCreateView(BaseAssignmentCreateView):
    model = MedicationAssignment
    form_class = MedicationAssignmentForm
    assignment_type = 'medication'

    def form_valid(self, form):
        medication = form.cleaned_data.get('medication')
        patient_weight = form.cleaned_data.get('patient_weight')
        dosage_per_kg = form.cleaned_data.get('dosage_per_kg')
        if medication and dosage_per_kg is not None and patient_weight is not None:
            calculated_dosage_value = dosage_per_kg * patient_weight
            form.instance.dosage = f"{calculated_dosage_value:.2f} {medication.default_dosage_per_kg_unit or ''}"
        elif medication and medication.default_dosage:
            form.instance.dosage = medication.default_dosage
        return super().form_valid(form)

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


class TreatmentAssignmentDetailView(LoginRequiredMixin, DetailView):
    """Динамический просмотр деталей любого типа назначения."""
    template_name = 'treatment_assignments/detail.html'
    context_object_name = 'assignment'

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        models_to_check = [MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment,
                           InstrumentalProcedureAssignment]
        for model in models_to_check:
            try:
                # Используем select_related для оптимизации
                return model.objects.select_related('patient', 'assigning_doctor', 'content_type').get(pk=pk)
            except model.DoesNotExist:
                continue
        raise Http404("Назначение не найдено")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Детали назначения №{self.object.pk}"
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.object))
        return context


class TreatmentAssignmentUpdateView(LoginRequiredMixin, UpdateView):
    """Динамическое редактирование любого типа назначения."""
    template_name = 'treatment_assignments/form.html'

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        models_to_check = [MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment,
                           InstrumentalProcedureAssignment]
        for model in models_to_check:
            try:
                return model.objects.get(pk=pk)
            except model.DoesNotExist:
                continue
        raise Http404("Назначение не найдено")

    def get_form_class(self):
        if isinstance(self.object, MedicationAssignment): return MedicationAssignmentForm
        if isinstance(self.object, GeneralTreatmentAssignment): return GeneralTreatmentAssignmentForm
        if isinstance(self.object, LabTestAssignment): return LabTestAssignmentForm
        if isinstance(self.object, InstrumentalProcedureAssignment): return InstrumentalProcedureAssignmentForm
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактировать назначение'
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.object))
        context['parent_object'] = self.object.content_object
        if isinstance(self.object, MedicationAssignment):
            context['assignment_type'] = 'medication'
        elif isinstance(self.object, GeneralTreatmentAssignment):
            context['assignment_type'] = 'general'
        elif isinstance(self.object, LabTestAssignment):
            context['assignment_type'] = 'lab'
        elif isinstance(self.object, InstrumentalProcedureAssignment):
            context['assignment_type'] = 'instrumental'
        return context

    def get_success_url(self):
        return reverse('treatment_assignments:assignment_detail', kwargs={'pk': self.object.pk})


class TreatmentAssignmentDeleteView(LoginRequiredMixin, DeleteView):
    """Динамическое удаление любого типа назначения."""
    template_name = 'treatment_assignments/confirm_delete.html'
    context_object_name = 'assignment'

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        models_to_check = [MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment,
                           InstrumentalProcedureAssignment]
        for model in models_to_check:
            try:
                return model.objects.get(pk=pk)
            except model.DoesNotExist:
                continue
        raise Http404("Назначение не найдено")

    def get_success_url(self):
        return self.request.GET.get('next', get_treatment_assignment_back_url(self.object))


# --- Ваши новые View ---

class DailyTreatmentPlanView(LoginRequiredMixin, View):
    """Ваш View для отображения листа назначений. Сохранен и немного оптимизирован."""
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
            today = timezone.localdate()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)

        # Оптимизированный запрос для получения всех активных назначений в диапазоне
        q_active_in_range = Q(start_date__date__lte=end_date) & (
                    Q(end_date__date__gte=start_date) | Q(end_date__isnull=True))

        med_qs = MedicationAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related(
            'medication')
        gen_qs = GeneralTreatmentAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related(
            'general_treatment')
        lab_qs = LabTestAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related('lab_test')
        inst_qs = InstrumentalProcedureAssignment.objects.filter(Q(patient=patient) & q_active_in_range).select_related(
            'instrumental_procedure')

        all_assignments = list(chain(med_qs, gen_qs, lab_qs, inst_qs))

        daily_plan_data = {
            start_date + timedelta(days=i): {'medications': [], 'general_treatments': [], 'lab_tests': [],
                                             'instrumental_procedures': []} for i in
            range((end_date - start_date).days + 1)}

        for assignment in all_assignments:
            assignment_start = assignment.start_date.date()
            assignment_end = assignment.end_date.date() if assignment.end_date else end_date

            current_date = max(assignment_start, start_date)
            while current_date <= min(assignment_end, end_date):
                if isinstance(assignment, MedicationAssignment):
                    daily_plan_data[current_date]['medications'].append(assignment)
                elif isinstance(assignment, GeneralTreatmentAssignment):
                    daily_plan_data[current_date]['general_treatments'].append(assignment)
                elif isinstance(assignment, LabTestAssignment):
                    daily_plan_data[current_date]['lab_tests'].append(assignment)
                elif isinstance(assignment, InstrumentalProcedureAssignment):
                    daily_plan_data[current_date]['instrumental_procedures'].append(assignment)
                current_date += timedelta(days=1)

        context = {
            'patient': patient,
            'parent_obj': parent_obj,
            'daily_plan_data': daily_plan_data,
            'dates': list(daily_plan_data.keys()),
            'start_date': start_date,
            'end_date': end_date,
            'title': f'Лист назначений для {patient.full_name}',
        }
        return render(request, self.template_name, context)


class TreatmentAssignmentListView(LoginRequiredMixin, ListView):
    """Улучшенный список, который показывает все типы назначений."""
    template_name = 'treatment_assignments/list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        # Собираем все назначения из всех моделей
        med_qs = MedicationAssignment.objects.all().select_related('patient', 'medication')
        gen_qs = GeneralTreatmentAssignment.objects.all().select_related('patient', 'general_treatment')
        lab_qs = LabTestAssignment.objects.all().select_related('patient', 'lab_test')
        inst_qs = InstrumentalProcedureAssignment.objects.all().select_related('patient', 'instrumental_procedure')

        # Объединяем и сортируем. Сортировка в памяти может быть неэффективной на больших данных.
        # Для больших объемов данных лучше использовать более сложные подходы (например, UNION в SQL).
        all_assignments = sorted(
            chain(med_qs, gen_qs, lab_qs, inst_qs),
            key=lambda x: x.start_date,
            reverse=True
        )
        return all_assignments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Все назначения'
        return context
