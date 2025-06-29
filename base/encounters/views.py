from django.db import models
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404
from .models import Encounter
from patients.models import Patient
from .forms import EncounterForm

class EncounterDetailView(DetailView):
    model = Encounter
    template_name = 'encounters/detail.html'
    context_object_name = 'encounter'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        
        context['documents'] = encounter.documents.all()
        context['encounter_number'] = Encounter.objects.filter(
            patient_id=encounter.patient_id,
            date_start__lt=encounter.date_start
        ).count() + 1
        return context

class EncounterCreateView(CreateView):
    model = Encounter
    form_class = EncounterForm
    template_name = 'encounters/form.html'

    def setup(self, request, *args, **kwargs):
        """Получаем пациента до основной логики."""
        super().setup(request, *args, **kwargs)
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])

    def form_valid(self, form):
        """Добавляем пациента и врача перед сохранением."""
        form.instance.patient = self.patient
        form.instance.doctor = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавляем в контекст пациента и заголовок."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['title'] = 'Новое обращение'
        return context
    
    def get_success_url(self):
        """Редирект после успешного создания."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterUpdateView(UpdateView):
    model = Encounter
    form_class = EncounterForm
    template_name = 'encounters/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['title'] = 'Редактировать обращение'
        return context

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterDeleteView(DeleteView):
    model = Encounter
    template_name = 'encounters/confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

    def get_context_data(self, **kwargs):
        """Добавляем номер обращения для страницы подтверждения."""
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        context['encounter_number'] = Encounter.objects.filter(
            patient_id=encounter.patient_id,
            date_start__lt=encounter.date_start
        ).count() + 1
        return context