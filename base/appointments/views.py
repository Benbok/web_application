# appointments/views.py
from rest_framework import viewsets
from django.views.generic import TemplateView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import AppointmentEvent
from .serializers import AppointmentEventSerializer
from .forms import AppointmentEventForm

class AppointmentEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления событиями приемов.
    Полностью поддерживает CRUD через Django REST Framework.
    """
    queryset = AppointmentEvent.objects.all()
    serializer_class = AppointmentEventSerializer

    def get_queryset(self):
        """
        Здесь можно добавить фильтрацию по врачу, дате или статусу.
        Например, фильтрация по доктору:
        ?doctor=<id>
        """
        queryset = super().get_queryset()
        doctor_id = self.request.query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset


class CalendarView(TemplateView):
    """
    Представление для отображения календаря через TemplateView.
    """
    template_name = "appointments/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointments'] = AppointmentEvent.objects.all()
        return context


class AppointmentCreateView(CreateView):
    model = AppointmentEvent
    form_class = AppointmentEventForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')


class AppointmentUpdateView(UpdateView):
    model = AppointmentEvent
    form_class = AppointmentEventForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')
