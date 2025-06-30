# treatment_assignments/views.py
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from .models import TreatmentAssignment
from .forms import TreatmentAssignmentForm
from patients.models import Patient
from departments.models import PatientDepartmentStatus # Предполагаем, что это ваш основной родительский объект

# Вспомогательная функция для определения URL возврата
def get_treatment_assignment_back_url(obj_or_parent_obj):
    """
    Определяет динамический URL по умолчанию для кнопки "Назад" или редиректа после действия.
    """
    parent_obj = None
    if isinstance(obj_or_parent_obj, TreatmentAssignment):
        parent_obj = obj_or_parent_obj.content_object
    else:
        parent_obj = obj_or_parent_obj

    if parent_obj:
        content_type = ContentType.objects.get_for_model(parent_obj)
        if content_type.model == 'patientdepartmentstatus':
            return reverse('departments:patient_history', kwargs={'pk': parent_obj.pk})
        elif content_type.model == 'patient':
            return reverse('patients:patient_detail', kwargs={'pk': parent_obj.pk})
        # Добавьте другие условия для других типов родительских объектов
    return reverse_lazy('treatment_assignments:assignment_list')


class TreatmentAssignmentDetailView(LoginRequiredMixin, DetailView):
    model = TreatmentAssignment
    template_name = 'treatment_assignments/detail.html'
    context_object_name = 'assignment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Назначение лечения №{self.object.pk}"
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.object))
        return context

class TreatmentAssignmentCreateView(LoginRequiredMixin, CreateView):
    model = TreatmentAssignment
    form_class = TreatmentAssignmentForm
    template_name = 'treatment_assignments/form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.model_name = self.kwargs.get('model_name')
        self.object_id = self.kwargs.get('object_id')
        
        if self.model_name and self.object_id:
            content_type_model = get_object_or_404(ContentType, model=self.model_name)
            self.parent_object = content_type_model.get_object_for_this_type(pk=self.object_id)
            if isinstance(self.parent_object, PatientDepartmentStatus):
                self.patient_object = self.parent_object.patient
            elif isinstance(self.parent_object, Patient):
                self.patient_object = self.parent_object
            else:
                self.patient_object = None
        else:
            self.parent_object = None
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
        context['title'] = 'Создать новое назначение лечения'
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.parent_object))
        context['parent_object'] = self.parent_object
        return context

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return get_treatment_assignment_back_url(self.object)


class TreatmentAssignmentUpdateView(LoginRequiredMixin, UpdateView):
    model = TreatmentAssignment
    form_class = TreatmentAssignmentForm
    template_name = 'treatment_assignments/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактировать назначение лечения'
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.object))
        context['parent_object'] = self.object.content_object
        return context

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('treatment_assignments:assignment_detail', kwargs={'pk': self.object.pk})

class TreatmentAssignmentDeleteView(LoginRequiredMixin, DeleteView):
    model = TreatmentAssignment
    template_name = 'treatment_assignments/confirm_delete.html'
    context_object_name = 'assignment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удалить назначение лечения'
        context['next_url'] = self.request.GET.get('next', get_treatment_assignment_back_url(self.object))
        return context
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('departments:department_list') 


class TreatmentAssignmentListView(LoginRequiredMixin, ListView):
    model = TreatmentAssignment
    template_name = 'treatment_assignments/list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Список назначений лечения'
        return context