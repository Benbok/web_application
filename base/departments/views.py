from django.db.models import Q
from django.views.generic import ListView, DetailView, View, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

from .models import Department, PatientDepartmentStatus 
from documents.models import ClinicalDocument
from .forms import DocumentAndAssignmentFilterForm # Импортируем новую форму

from treatment_assignments.models import MedicationAssignment

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

        assignments = MedicationAssignment.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
        )

        if filter_form.is_valid():
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            author = filter_form.cleaned_data.get('author')
            document_type = filter_form.cleaned_data.get('document_type') # Получаем выбранный тип документа
            search_query = filter_form.cleaned_data.get('search_query')

            print(f"[DEBUG] Filter form cleaned data: start_date={start_date}, end_date={end_date}, author={author}, document_type={document_type}, search_query={search_query}")

            if start_date:
                documents = documents.filter(datetime_document__date__gte=start_date)
                assignments = assignments.filter(start_date__date__gte=start_date)
            if end_date:
                documents = documents.filter(datetime_document__date__lte=end_date)
                assignments = assignments.filter(start_date__date__lte=end_date)
            if author:
                documents = documents.filter(author=author)
                assignments = assignments.filter(assigning_doctor=author)
            if document_type: # Добавляем фильтрацию по типу документа
                documents = documents.filter(document_type=document_type)
            if search_query:
                # Для документов ищем в JSONField 'data'
                documents = documents.filter(Q(data__icontains=search_query) | Q(document_type__name__icontains=search_query))
                # Для назначений ищем в treatment_name и notes
                assignments = assignments.filter(Q(treatment_name__icontains=search_query) | Q(notes__icontains=search_query))

        return documents.order_by('-datetime_document'), assignments.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_status = self.get_object()
        department = patient_status.department # Получаем объект отделения

        # Обработка фильтров из GET-запроса
        filter_form = DocumentAndAssignmentFilterForm(self.request.GET, department=department) # Передаем department в форму
        # Получаем отфильтрованные документы и назначения
        documents, assignments = self.get_filtered_documents_and_assignments(patient_status, filter_form)

        # Пагинация (раздельная)
        documents_paginator = Paginator(documents, 10)
        documents_page_number = self.request.GET.get('daily_notes_page')
        documents_page_obj = documents_paginator.get_page(documents_page_number)

        assignments_paginator = Paginator(assignments, 10)
        assignments_page_number = self.request.GET.get('assignments_page')
        assignments_page_obj = assignments_paginator.get_page(assignments_page_number)

        context['filter_form'] = filter_form # Передаем форму фильтра в контекст
        context['daily_notes_page_obj'] = documents_page_obj
        context['assignments_page_obj'] = assignments_page_obj
        context['title'] = f"История пациента: {patient_status.patient.full_name} в {patient_status.department.name}"

        # Получаем активные назначения для этого patient_status
        active_assignments = MedicationAssignment.objects.filter(
            content_type=ContentType.objects.get_for_model(PatientDepartmentStatus),
            object_id=patient_status.pk,
            status='active',
        ).order_by('-start_date')
        context['active_assignments'] = active_assignments

        # Получаем неактивные (завершенные, отмененные, приостановленные) назначения
        inactive_assignments = MedicationAssignment.objects.filter(
            content_type=ContentType.objects.get_for_model(PatientDepartmentStatus),
            object_id=patient_status.pk,
            status__in=['completed', 'canceled', 'paused'],
        ).order_by('-start_date')
        context['inactive_assignments'] = inactive_assignments

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