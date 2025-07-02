# departments/views.py
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
from documents.forms import ClinicalDocumentFilterForm, ClinicalDocumentForm
from treatment_assignments.models import TreatmentAssignment

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

        context['title'] = f"Отделение: {department.name}"
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
        content_type = ContentType.objects.get_for_model(PatientDepartmentStatus)
        documents = ClinicalDocument.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
        )
        assignments = TreatmentAssignment.objects.filter(
            content_type=content_type,
            object_id=patient_status.pk
        )
        if filter_form.is_valid():
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            author = filter_form.cleaned_data.get('author')
            search_query = filter_form.cleaned_data.get('search_query')

            if start_date:
                documents = documents.filter(created_at__date__gte=start_date)
                assignments = assignments.filter(created_at__date__gte=start_date)
            if end_date:
                documents = documents.filter(created_at__date__lte=end_date)
                assignments = assignments.filter(created_at__date__lte=end_date)
            if author:
                documents = documents.filter(author=author)
                # assignments: фильтрация по author только если поле есть
                if hasattr(TreatmentAssignment, 'author'):
                    assignments = assignments.filter(author=author)
            if search_query:
                documents = documents.filter(
                    Q(title__icontains=search_query) | Q(content__icontains=search_query)
                )
                assignments = assignments.filter(
                    Q(title__icontains=search_query) | Q(content__icontains=search_query)
                )
        return documents.order_by('-created_at'), assignments.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_status = self.get_object()

        # Обработка фильтров из GET-запроса
        filter_form = ClinicalDocumentFilterForm(self.request.GET)
        # Получаем отфильтрованные документы и назначения
        documents, assignments = self.get_filtered_documents_and_assignments(patient_status, filter_form)

        # Пагинация (раздельная)
        documents_paginator = Paginator(documents, 10)
        documents_page_number = self.request.GET.get('daily_notes_page')
        documents_page_obj = documents_paginator.get_page(documents_page_number)

        assignments_paginator = Paginator(assignments, 10)
        assignments_page_number = self.request.GET.get('assignments_page')
        assignments_page_obj = assignments_paginator.get_page(assignments_page_number)

        context['clinical_documents_filter_form'] = filter_form
        context['daily_notes_page_obj'] = documents_page_obj
        context['assignments_page_obj'] = assignments_page_obj
        context['title'] = f"История пациента: {patient_status.patient.full_name} в {patient_status.department.name}"
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