import logging
from django.db.models import Q
from django.views.generic import ListView, DetailView, View, UpdateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

from .models import Department, PatientDepartmentStatus
from documents.models import ClinicalDocument
from .forms import DocumentAndAssignmentFilterForm, PatientAcceptanceForm
# Импорты treatment_assignments удалены - больше не нужны
from treatment_management.models import TreatmentPlan, TreatmentMedication
from examination_management.models import ExaminationPlan

logger = logging.getLogger(__name__)


class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'departments/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        return Department.objects.exclude(slug='admission')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Отделения"
        return context


class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'departments/department_detail.html'
    context_object_name = 'department'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = self.get_object()
        # Удалены все отладочные print-выводы
        pending_patients = PatientDepartmentStatus.all_objects.filter(
            department=department, status='pending'
        ).select_related('patient').order_by('admission_date')
        context['pending_patients'] = pending_patients
        context['accepted_patients'] = PatientDepartmentStatus.objects.filter(
            department=department, status='accepted'
        ).select_related('patient').order_by('acceptance_date')
        context['title'] = f"Отделение: {department.name}"
        return context


class PatientDepartmentAcceptView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        patient_status = get_object_or_404(PatientDepartmentStatus, pk=pk)

        if patient_status.department.pk != self.kwargs.get('department_pk'):
            messages.error(request, "Ошибка: Неверное отделение для принятия пациента.")
            return redirect(
                reverse('departments:department_detail', kwargs={'pk': self.kwargs['department_pk']})
            )

        if patient_status.accept_patient(request.user):
            messages.success(
                request,
                f"Пациент {patient_status.patient.full_name} успешно принят в отделение «{patient_status.department.name}».",
            )
        else:
            messages.warning(request, "Пациент уже принят или имеет другой статус.")

        return redirect(
            reverse('departments:department_detail', kwargs={'pk': patient_status.department.pk})
        )


class PatientDepartmentHistoryView(LoginRequiredMixin, DetailView):
    model = PatientDepartmentStatus
    template_name = 'departments/patient_history.html'
    context_object_name = 'patient_status'

    def get_filter_form(self):
        """Создает форму фильтрации для документов и назначений"""
        return DocumentAndAssignmentFilterForm(self.request.GET, department=self.get_object().department)

    def get_filtered_documents_and_assignments(self, patient_status, filter_form):
        # Теперь используем прямые связи для departments
        documents = patient_status.clinical_documents.all().select_related('document_type', 'author')
        treatment_plans = patient_status.treatment_plans.all().prefetch_related(
            'medications__medication',
            'medications__route'
        )
        examination_plans = patient_status.examination_plans.all()
        
        # Назначения treatment_assignments удалены - больше не нужны
        general_treatment_assignments = []

        # Получаем препараты из планов лечения
        treatment_medications = []
        for plan in treatment_plans:
            for medication in plan.medications.all():
                treatment_medications.append({
                    'plan': plan,
                    'medication': medication,
                    'created_date': plan.created_at,
                    'created_by': plan.created_by
                })

        # Применяем фильтры
        if filter_form.is_valid():
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            author = filter_form.cleaned_data.get('author')
            document_type = filter_form.cleaned_data.get('document_type')
            search_query = filter_form.cleaned_data.get('search_query')

            if start_date:
                documents = documents.filter(created_at__date__gte=start_date)
                # general_treatment_assignments = general_treatment_assignments.filter(created_at__date__gte=start_date)  # УДАЛЕНО
                treatment_plans = treatment_plans.filter(created_at__date__gte=start_date)
                examination_plans = examination_plans.filter(created_at__date__gte=start_date)

            if end_date:
                documents = documents.filter(created_at__date__lte=end_date)
                # general_treatment_assignments = general_treatment_assignments.filter(created_at__date__lte=end_date)  # УДАЛЕНО
                treatment_plans = treatment_plans.filter(created_at__date__lte=end_date)
                examination_plans = examination_plans.filter(created_at__date__lte=end_date)

            if author:
                documents = documents.filter(author__username__icontains=author)
                # general_treatment_assignments = general_treatment_assignments.filter(assigning_doctor__username__icontains=author)  # УДАЛЕНО
                treatment_plans = treatment_plans.filter(created_by__username__icontains=author)
                examination_plans = examination_plans.filter(created_by__username__icontains=author)

            if document_type:
                documents = documents.filter(document_type=document_type)

            if search_query:
                documents = documents.filter(
                    Q(data__icontains=search_query) |
                    Q(document_type__name__icontains=search_query)
                )
                # general_treatment_assignments = general_treatment_assignments.filter(  # УДАЛЕНО
                #     Q(general_treatment__icontains=search_query) |
                #     Q(notes__icontains=search_query)
                # )
                treatment_plans = treatment_plans.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
                examination_plans = examination_plans.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )

        return {
            'documents': documents,
            'general_treatment_assignments': general_treatment_assignments,
            'treatment_plans': treatment_plans,
            'treatment_medications': treatment_medications,
            'examination_plans': examination_plans,
        }

    def paginate_queryset(self, queryset, page_param, per_page=10):
        paginator = Paginator(queryset, per_page)
        page_number = self.request.GET.get(page_param)
        return paginator.get_page(page_number)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_status = self.get_object()
        filter_form = self.get_filter_form()

        # Получаем отфильтрованные данные
        filtered_data = self.get_filtered_documents_and_assignments(patient_status, filter_form)
        
        # Пагинируем данные
        documents_page_obj = self.paginate_queryset(
            filtered_data['documents'].order_by('-created_at'), 
            'documents_page'
        )
        # general_treatment_assignments_page_obj = self.paginate_queryset(  # УДАЛЕНО
        #     filtered_data['general_treatment_assignments'].order_by('-created_at'), 
        #     'general_treatment_assignments_page'
        # )
        treatment_plans_page_obj = self.paginate_queryset(
            filtered_data['treatment_plans'].order_by('-created_at'), 
            'treatment_plans_page'
        )
        treatment_medications_page_obj = self.paginate_queryset(
            filtered_data['treatment_medications'], 
            'treatment_medications_page'
        )
        examination_plans_page_obj = self.paginate_queryset(
            filtered_data['examination_plans'].order_by('-created_at'),
            'examination_plans_page'
        )

        context.update({
            'title': f"История пациента: {patient_status.patient.get_full_name_with_age()} в {patient_status.department.name}",
            'patient_status': patient_status,
            'patient': patient_status.patient,
            'department': patient_status.department,
            'filter_form': filter_form,
            'documents_page_obj': documents_page_obj,
            # 'general_treatment_assignments_page_obj': general_treatment_assignments_page_obj,  # УДАЛЕНО
            'treatment_plans_page_obj': treatment_plans_page_obj,
            'treatment_medications_page_obj': treatment_medications_page_obj,
            'examination_plans_page_obj': examination_plans_page_obj,
        })

        return context


class PatientAcceptanceView(LoginRequiredMixin, UpdateView):
    model = PatientDepartmentStatus
    form_class = PatientAcceptanceForm
    template_name = 'departments/acceptance_form.html'
    context_object_name = 'patient_status'

    def form_valid(self, form):
        patient_status = form.save(commit=False)
        patient_status.status = 'accepted'
        patient_status.accepted_by = self.request.user
        patient_status.save()
        messages.success(self.request, f"Пациент {patient_status.patient.full_name} успешно принят в отделение.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.request.GET.get('next', reverse('departments:department_detail', kwargs={'pk': self.object.department.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Принятие пациента: {self.object.patient.full_name}"
        context['next_url'] = self.get_success_url()
        return context


class PatientDepartmentDischargeView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        patient_status = get_object_or_404(PatientDepartmentStatus, pk=pk)

        if patient_status.department.pk != self.kwargs.get('department_pk'):
            messages.error(request, "Ошибка: Неверное отделение для выписки пациента.")
            return redirect(reverse('departments:department_detail', kwargs={'pk': self.kwargs['department_pk']}))

        if patient_status.discharge_patient():
            messages.success(request, f"Пациент {patient_status.patient.full_name} успешно выписан из отделения «{patient_status.department.name}».")
        else:
            messages.warning(request, "Пациент уже выписан или не находится в статусе 'принят'.")

        return redirect(reverse('departments:department_detail', kwargs={'pk': patient_status.department.pk}))
