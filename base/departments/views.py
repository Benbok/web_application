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
from treatment_assignments.models import MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment, InstrumentalProcedureAssignment

class DepartmentListView(ListView):
    model = Department
    template_name = 'departments/department_list.html'
    context_object_name = 'departments'
    
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
        
        # Получаем пациентов, ожидающих принятия в этом отделении
        context['pending_patients'] = PatientDepartmentStatus.objects.filter(
            department=department,
            status='pending'
        ).select_related('patient').order_by('admission_date')

        # Получаем пациентов, принятых в этом отделении
        context['accepted_patients'] = PatientDepartmentStatus.objects.filter(
            department=department,
            status='accepted'
        ).select_related('patient').order_by('acceptance_date')

        context['title'] = "Отделение: {department.name}"
        return context

class PatientDepartmentAcceptView(LoginRequiredMixin, View):
    """
    Представление для принятия пациента в отделение.
    """
    def post(self, request, pk, *args, **kwargs):
        patient_status = get_object_or_404(PatientDepartmentStatus, pk=pk)

        if patient_status.department.pk != self.kwargs.get('department_pk'):
             messages.error(request, "Ошибка: Неверное отделение для принятия пациента.")
             return redirect(reverse('departments:department_detail', kwargs={'pk': self.kwargs['department_pk']}))


        if patient_status.accept_patient(request.user):
            messages.success(request, f"Пациент {patient_status.patient.full_name} успешно принят в отделение «{patient_status.department.name}».")
        else:
            messages.warning(request, "Пациент уже принят или имеет другой статус.")

        return redirect(reverse('departments:department_detail', kwargs={'pk': patient_status.department.pk}))

class PatientDepartmentHistoryView(LoginRequiredMixin, DetailView):
    model = PatientDepartmentStatus
    template_name = 'departments/patient_history.html'
    context_object_name = 'patient_status'

    def get_filtered_documents_and_assignments(self, patient_status, filter_form):
        """
        Вспомогательный метод для фильтрации документов и назначений по форме.
        """
        print(f"[DEBUG] Filtering for PatientDepartmentStatus ID: {patient_status.pk}")
        print(f"[DEBUG] PatientDepartmentStatus Department: {patient_status.department.name} (ID: {patient_status.department.pk})")

        content_type = ContentType.objects.get_for_model(PatientDepartmentStatus)
        print(f"[DEBUG] ContentType for PatientDepartmentStatus: {content_type.model} (ID: {content_type.pk})")

        documents = ClinicalDocument.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk,
            document_type__department=patient_status.department # Добавляем фильтрацию по отделению
        )
        print(f"[DEBUG] Initial documents queryset count (filtered by department): {documents.count()}")
        for doc in documents:
            print(f"[DEBUG] Initial document: {doc.document_type.name} (Department: {doc.document_type.department.name if doc.document_type.department else 'None'})")

        # Получаем все типы назначений
        medication_assignments = MedicationAssignment.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')
        general_treatment_assignments = GeneralTreatmentAssignment.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')
        lab_test_assignments = LabTestAssignment.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
        ).select_related('assigning_doctor__doctor_profile', 'completed_by__doctor_profile')
        instrumental_procedure_assignments = InstrumentalProcedureAssignment.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_status = self.get_object()
        department = patient_status.department

        filter_form = DocumentAndAssignmentFilterForm(self.request.GET, department=department)
        documents, medication_assignments, general_treatment_assignments, lab_test_assignments, instrumental_procedure_assignments = self.get_filtered_documents_and_assignments(patient_status, filter_form)

        documents_paginator = Paginator(documents, 10)
        documents_page_number = self.request.GET.get('daily_notes_page')
        documents_page_obj = documents_paginator.get_page(documents_page_number)

        medication_assignments_paginator = Paginator(medication_assignments, 10)
        medication_assignments_page_number = self.request.GET.get('medication_assignments_page')
        medication_assignments_page_obj = medication_assignments_paginator.get_page(medication_assignments_page_number)

        general_treatment_assignments_paginator = Paginator(general_treatment_assignments, 10)
        general_treatment_assignments_page_number = self.request.GET.get('general_treatment_assignments_page')
        general_treatment_assignments_page_obj = general_treatment_assignments_paginator.get_page(general_treatment_assignments_page_number)

        lab_test_assignments_paginator = Paginator(lab_test_assignments, 10)
        lab_test_assignments_page_number = self.request.GET.get('lab_test_assignments_page')
        lab_test_assignments_page_obj = lab_test_assignments_paginator.get_page(lab_test_assignments_page_number)

        instrumental_procedure_assignments_paginator = Paginator(instrumental_procedure_assignments, 10)
        instrumental_procedure_assignments_page_number = self.request.GET.get('instrumental_procedure_assignments_page')
        instrumental_procedure_assignments_page_obj = instrumental_procedure_assignments_paginator.get_page(instrumental_procedure_assignments_page_number)

        context['filter_form'] = filter_form
        context['daily_notes_page_obj'] = documents_page_obj
        context['medication_assignments_page_obj'] = medication_assignments_page_obj
        context['general_treatment_assignments_page_obj'] = general_treatment_assignments_page_obj
        context['lab_test_assignments_page_obj'] = lab_test_assignments_page_obj
        context['instrumental_procedure_assignments_page_obj'] = instrumental_procedure_assignments_page_obj
        context['title'] = f"История пациента: {patient_status.patient.full_name} в {patient_status.department.name}"

        # Собираем все активные и неактивные назначения для верхних блоков
        all_active_assignments = []
        all_inactive_assignments = []

        for assignment_page_obj in [
            medication_assignments_page_obj,
            general_treatment_assignments_page_obj,
            lab_test_assignments_page_obj,
            instrumental_procedure_assignments_page_obj,
        ]:
            for assignment in assignment_page_obj.object_list:
                if isinstance(assignment, MedicationAssignment) and assignment.status == 'active':
                    all_active_assignments.append(assignment)
                elif isinstance(assignment, MedicationAssignment) and assignment.status in ['completed', 'canceled', 'paused']:
                    all_inactive_assignments.append(assignment)
        
        # Сортируем по дате начала (для активных) и дате обновления (для неактивных)
        context['active_assignments'] = sorted(all_active_assignments, key=lambda x: x.start_date, reverse=True)
        context['inactive_assignments'] = sorted(all_inactive_assignments, key=lambda x: x.updated_at, reverse=True)

        return context


class PatientAcceptanceView(LoginRequiredMixin, UpdateView):
    model = PatientDepartmentStatus
    form_class = PatientAcceptanceForm
    template_name = 'departments/acceptance_form.html' # Мы создадим этот шаблон
    context_object_name = 'patient_status'

    def form_valid(self, form):
        """Переопределяем метод, чтобы обновить статус при сохранении."""
        patient_status = form.save(commit=False)
        patient_status.status = 'accepted'
        patient_status.accepted_by = self.request.user
        patient_status.save()
        messages.success(self.request, f"Пациент {patient_status.patient.full_name} успешно принят в отделение.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        """
        Перенаправляет на URL из параметра 'next', если он есть.
        В противном случае - на страницу отделения.
        """
        return self.request.GET.get('next', reverse('departments:department_detail', kwargs={'pk': self.object.department.pk}))

    def get_context_data(self, **kwargs):
        """
        Передаем URL для возврата в контекст шаблона для кнопки "Отмена".
        """
        context = super().get_context_data(**kwargs)
        context['title'] = f"Принятие пациента: {self.object.patient.full_name}"
        # Используем тот же метод, что и для get_success_url
        context['next_url'] = self.get_success_url()
        return context

class PatientDepartmentDischargeView(LoginRequiredMixin, View):
    """
    Представление для выписки пациента из отделения.
    """
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