from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from .models import Appointment
from .forms import AppointmentForm


class AppointmentListView(ListView):
    model = Appointment
    template_name = 'appointments/calendar.html'
    context_object_name = 'appointments'


class AppointmentCreateView(CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')