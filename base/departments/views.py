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
from treatment_management.models import TreatmentPlan, TreatmentMedication
from examination_management.models import ExaminationPlan

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

    def get_filter_form(self):
        """Создает форму фильтрации для документов и назначений"""
        return DocumentAndAssignmentFilterForm(self.request.GET, department=self.get_object().department)

    def get_filtered_documents_and_assignments(self, patient_status, filter_form):
        content_type = ContentType.objects.get_for_model(PatientDepartmentStatus)

        # Получаем все документы для данного пациента
        all_documents = ClinicalDocument.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk,
        )
        
        # Получаем документы, отфильтрованные по отделению
        # Временно убираем фильтрацию для отладки
        documents = all_documents  # .filter(document_type__department=patient_status.department)
        
        # Отладочная информация
        print(f"DEBUG: Всего документов для пациента {patient_status.pk}: {all_documents.count()}")
        print(f"DEBUG: Документов после фильтрации по отделению {patient_status.department.name}: {documents.count()}")
        if documents.exists():
            print(f"DEBUG: Типы документов: {[doc.document_type.name for doc in documents[:5]]}")
        else:
            print(f"DEBUG: Нет документов после фильтрации по отделению")
            # Показываем все документы для отладки
            print(f"DEBUG: Все документы: {[(doc.document_type.name, doc.document_type.department.name if doc.document_type.department else 'None') for doc in all_documents[:5]]}")

        general_treatment_assignments = GeneralTreatmentAssignment.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')

        # Получаем планы лечения и их препараты
        treatment_plans = TreatmentPlan.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        ).prefetch_related(
            'medications__medication',
            'medications__route'
        )

        # Получаем препараты из планов лечения
        treatment_medications = []
        for plan in treatment_plans:
            for medication in plan.medications.all():
                treatment_medications.append({
                    'plan': plan,
                    'medication': medication,
                    'created_date': plan.created_at,
                    'created_by': None  # В модели TreatmentPlan нет поля created_by
                })

        # Получаем планы обследования
        examination_plans = ExaminationPlan.objects.filter(
            content_type=content_type, object_id=patient_status.pk
        )

        # Применяем фильтры
        if filter_form.is_valid():
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            author = filter_form.cleaned_data.get('author')
            document_type = filter_form.cleaned_data.get('document_type')
            search_query = filter_form.cleaned_data.get('search_query')

            if start_date:
                documents = documents.filter(created_at__date__gte=start_date)
                general_treatment_assignments = general_treatment_assignments.filter(created_at__date__gte=start_date)
                treatment_plans = treatment_plans.filter(created_at__date__gte=start_date)
                examination_plans = examination_plans.filter(created_at__date__gte=start_date)

            if end_date:
                documents = documents.filter(created_at__date__lte=end_date)
                general_treatment_assignments = general_treatment_assignments.filter(created_at__date__lte=end_date)
                treatment_plans = treatment_plans.filter(created_at__date__lte=end_date)
                examination_plans = examination_plans.filter(created_at__date__lte=end_date)

            if author:
                documents = documents.filter(author__username__icontains=author)
                general_treatment_assignments = general_treatment_assignments.filter(assigning_doctor__username__icontains=author)
                # В TreatmentPlan нет поля created_by, поэтому фильтр по автору не применяется

            if document_type:
                documents = documents.filter(document_type=document_type)

            if search_query:
                documents = documents.filter(
                    Q(data__icontains=search_query) |
                    Q(document_type__name__icontains=search_query)
                )
                general_treatment_assignments = general_treatment_assignments.filter(
                    Q(general_treatment__icontains=search_query) |
                    Q(notes__icontains=search_query)
                )
                treatment_plans = treatment_plans.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
                examination_plans = examination_plans.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )

        # Обновляем список препаратов после фильтрации
        treatment_medications = []
        for plan in treatment_plans:
            for medication in plan.medications.all():
                treatment_medications.append({
                    'plan': plan,
                    'medication': medication,
                    'created_date': plan.created_at,
                    'created_by': None  # В модели TreatmentPlan нет поля created_by
                })

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
        general_treatment_assignments_page_obj = self.paginate_queryset(
            filtered_data['general_treatment_assignments'].order_by('-created_at'), 
            'general_treatment_assignments_page'
        )
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
            'patient_status': patient_status,
            'patient': patient_status.patient,
            'department': patient_status.department,
            'filter_form': filter_form,
            'documents_page_obj': documents_page_obj,
            'general_treatment_assignments_page_obj': general_treatment_assignments_page_obj,
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
