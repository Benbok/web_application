from django.views.generic import ListView, CreateView, View, UpdateView
from django.http import JsonResponse
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

    def get_initial(self):
        date = self.request.GET.get('date')
        if date:
            return {'start_time': date}
        return super().get_initial()


class AppointmentEventsAPI(View):
    def get(self, request):
        appointments = Appointment.objects.all()
        events = []
        for appt in appointments:
            events.append({
                'title': f"{appt.patient} (Врач: {appt.doctor})",
                'start': appt.start_time.isoformat(),
                'end': appt.end_time.isoformat(),
            })
        return JsonResponse(events, safe=False)

class AppointmentUpdateView(UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')