# departments/views.py
from django.db.models import Q
from django.views.generic import ListView, DetailView, View, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

from .models import Department, PatientDepartmentStatus # Убедитесь, что PatientDepartmentStatus импортирован
from documents.models import ClinicalDocument
from documents.forms import ClinicalDocumentFilterForm

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_status = self.get_object()

        patient_status_content_type = ContentType.objects.get_for_model(PatientDepartmentStatus)

        # Обработка фильтров из GET-запроса
        filter_form = ClinicalDocumentFilterForm(self.request.GET)
        
        # Общий QuerySet для документов этого PatientDepartmentStatus
        base_documents_queryset = ClinicalDocument.objects.filter(
            content_type=patient_status_content_type,
            object_id=patient_status.pk
        ).order_by('-created_at')

        # Применяем фильтры к обоим QuerySet'ам
        filtered_documents_queryset = base_documents_queryset
        if filter_form.is_valid():
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            author = filter_form.cleaned_data.get('author')
            search_query = filter_form.cleaned_data.get('search_query')

            if start_date:
                filtered_documents_queryset = filtered_documents_queryset.filter(created_at__date__gte=start_date)
            if end_date:
                # Включаем весь конечный день
                filtered_documents_queryset = filtered_documents_queryset.filter(created_at__date__lte=end_date)
            if author:
                filtered_documents_queryset = filtered_documents_queryset.filter(author=author)
            if search_query:
                filtered_documents_queryset = filtered_documents_queryset.filter(
                    Q(title__icontains=search_query) | 
                    Q(content__icontains=search_query)
                )

        # Отдельные QuerySet'ы для дневников и осмотров
        daily_notes_queryset = filtered_documents_queryset

        # Пагинация для дневников
        daily_notes_paginator = Paginator(daily_notes_queryset, 10)
        daily_notes_page_number = self.request.GET.get('daily_notes_page')
        daily_notes_page_obj = daily_notes_paginator.get_page(daily_notes_page_number)


        context['clinical_documents_filter_form'] = filter_form
        context['daily_notes_page_obj'] = daily_notes_page_obj
        
        context['title'] = f"История пациента: {patient_status.patient.full_name} в {patient_status.department.name}"
        return context

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = ClinicalDocument
    # form_class = ClinicalDocumentForm # Ваша форма для ClinicalDocument
    fields = ['document_type', 'title', 'content', 'template'] # Пример полей, если нет отдельной формы

    template_name = 'documents/document_form.html' # Шаблон для создания документа

    def get_initial(self):
        initial = super().get_initial()
        model_name = self.kwargs.get('model_name')
        object_id = self.kwargs.get('object_id')

        if model_name and object_id:
            try:
                # Попытка получить объект ContentType
                content_type = ContentType.objects.get(app_label='departments', model=model_name) # Предполагаем app_label 'departments' для patientdepartmentstatus
                # Если нужен доступ к самому объекту, то:
                # related_object = content_type.get_object_for_this_type(pk=object_id)
                # initial['related_object'] = related_object # Если это нужно для формы
            except ContentType.DoesNotExist:
                pass # Обработать ошибку, если model_name не найден
        return initial

    def form_valid(self, form):
        model_name = self.kwargs.get('model_name')
        object_id = self.kwargs.get('object_id')

        if model_name and object_id:
            content_type = ContentType.objects.get(app_label='departments', model=model_name) # Или другой app_label
            form.instance.content_type = content_type
            form.instance.object_id = object_id

        form.instance.author = self.request.user # Устанавливаем текущего пользователя как автора

        # Если есть поле 'template' и оно заполнено, можно использовать его default_content
        # if form.instance.template and not form.cleaned_data.get('content'):
        #     form.instance.content = form.instance.template.default_content

        return super().form_valid(form)

    def get_success_url(self):
        # После создания документа, лучше вернуться на страницу истории пациента
        model_name = self.kwargs.get('model_name')
        object_id = self.kwargs.get('object_id')
        if model_name == 'patientdepartmentstatus':
            return reverse('departments:patient_history', kwargs={'pk': object_id})
        # Иначе, редирект на другую страницу, например, список документов или детали самого документа
        return reverse('documents:document_detail', kwargs={'pk': self.object.pk})

class DocumentDetailView(DetailView):
    model = ClinicalDocument
    template_name = 'documents/document_detail.html' # Шаблон для просмотра документа
    context_object_name = 'document'





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