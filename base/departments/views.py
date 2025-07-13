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
from treatment_assignments.models import (
    MedicationAssignment,
    GeneralTreatmentAssignment,
    LabTestAssignment,
    InstrumentalProcedureAssignment,
)

logger = logging.getLogger(__name__)


class DepartmentListView(ListView):
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

    def get_filtered_documents_and_assignments(self, patient_status, filter_form):
        content_type = ContentType.objects.get_for_model(PatientDepartmentStatus)

        documents = ClinicalDocument.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk,
            document_type__department=patient_status.department,
        )

        medication_assignments = MedicationAssignment.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')

        general_treatment_assignments = GeneralTreatmentAssignment.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')

        lab_test_assignments = LabTestAssignment.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')

        instrumental_procedure_assignments = InstrumentalProcedureAssignment.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')

        if filter_form.is_valid():
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            author = filter_form.cleaned_data.get('author')
            document_type = filter_form.cleaned_data.get('document_type')
            search_query = filter_form.cleaned_data.get('search_query')

            if start_date:
                documents = documents.filter(datetime_document__date__gte=start_date)
                medication_assignments = medication_assignments.filter(start_date__date__gte=start_date)
                general_treatment_assignments = general_treatment_assignments.filter(start_date__date__gte=start_date)
                lab_test_assignments = lab_test_assignments.filter(start_date__date__gte=start_date)
                instrumental_procedure_assignments = instrumental_procedure_assignments.filter(start_date__date__gte=start_date)
            if end_date:
                documents = documents.filter(datetime_document__date__lte=end_date)
                medication_assignments = medication_assignments.filter(start_date__date__lte=end_date)
                general_treatment_assignments = general_treatment_assignments.filter(start_date__date__lte=end_date)
                lab_test_assignments = lab_test_assignments.filter(start_date__date__lte=end_date)
                instrumental_procedure_assignments = instrumental_procedure_assignments.filter(start_date__date__lte=end_date)
            if author:
                documents = documents.filter(author=author)
                medication_assignments = medication_assignments.filter(assigning_doctor=author)
                general_treatment_assignments = general_treatment_assignments.filter(assigning_doctor=author)
                lab_test_assignments = lab_test_assignments.filter(assigning_doctor=author)
                instrumental_procedure_assignments = instrumental_procedure_assignments.filter(assigning_doctor=author)
            if document_type:
                documents = documents.filter(document_type=document_type)
            if search_query:
                documents = documents.filter(Q(data__icontains=search_query) | Q(document_type__name__icontains=search_query))
                medication_assignments = medication_assignments.filter(Q(medication__name__icontains=search_query) | Q(notes__icontains=search_query))
                general_treatment_assignments = general_treatment_assignments.filter(Q(general_treatment__name__icontains=search_query) | Q(notes__icontains=search_query))
                lab_test_assignments = lab_test_assignments.filter(Q(lab_test__name__icontains=search_query) | Q(notes__icontains=search_query))
                instrumental_procedure_assignments = instrumental_procedure_assignments.filter(Q(instrumental_procedure__name__icontains=search_query) | Q(notes__icontains=search_query))

        return (
            documents.order_by('-datetime_document'),
            medication_assignments.order_by('-start_date'),
            general_treatment_assignments.order_by('-start_date'),
            lab_test_assignments.order_by('-start_date'),
            instrumental_procedure_assignments.order_by('-start_date'),
        )

    def paginate_queryset(self, queryset, page_param, per_page=10):
        paginator = Paginator(queryset, per_page)
        page_number = self.request.GET.get(page_param)
        return paginator.get_page(page_number)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_status = self.get_object()
        department = patient_status.department

        filter_form = DocumentAndAssignmentFilterForm(self.request.GET, department=department)
        docs, meds, generals, labs, procedures = self.get_filtered_documents_and_assignments(patient_status, filter_form)

        context['filter_form'] = filter_form
        context['daily_notes_page_obj'] = self.paginate_queryset(docs, 'daily_notes_page')
        context['medication_assignments_page_obj'] = self.paginate_queryset(meds, 'medication_assignments_page')
        context['general_treatment_assignments_page_obj'] = self.paginate_queryset(generals, 'general_treatment_assignments_page')
        context['lab_test_assignments_page_obj'] = self.paginate_queryset(labs, 'lab_test_assignments_page')
        context['instrumental_procedure_assignments_page_obj'] = self.paginate_queryset(procedures, 'instrumental_procedure_assignments_page')
        context['title'] = f"История пациента: {patient_status.patient.full_name} в {patient_status.department.name}"

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
