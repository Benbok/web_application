# appointments/views.py
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, View
from .models import Appointment, AppointmentStatus
from .forms import AppointmentForm


class AppointmentEventsAPI(View):
    """
    API для FullCalendar. Возвращает записи в формате JSON.
    """

    def get(self, request, *args, **kwargs):
        appointments = Appointment.objects.select_related('patient', 'doctor').filter(
            status=AppointmentStatus.SCHEDULED)

        events = []
        for appt in appointments:
            events.append({
                'title': f"{appt.patient.full_name} -> Dr. {appt.doctor.last_name}",

                # ИСПРАВЛЕНИЕ: Форматируем дату в строку без часового пояса
                'start': appt.start_datetime.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': appt.end_datetime.strftime('%Y-%m-%dT%H:%M:%S'),

                'url': reverse_lazy('appointments:edit', args=[appt.id]),
            })
        return JsonResponse(events, safe=False)

class AppointmentListView(ListView):
    model = Appointment
    template_name = 'appointments/calendar.html'
    # Мы не передаем контекст, так как календарь получает данные через API

class AppointmentCreateView(CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')

class AppointmentUpdateView(UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')

def appointment_data(request):
    """
    API для FullCalendar. Возвращает записи в формате JSON.
    """
    appointments = Appointment.objects.filter(status=AppointmentStatus.SCHEDULED)
    events = []
    for appointment in appointments:
        events.append({
            'title': f"{appointment.patient.last_name} -> Dr. {appointment.doctor.last_name}",
            'start': appointment.start_datetime.isoformat(),
            'end': appointment.end_datetime.isoformat(),
            'url': reverse_lazy('appointments:edit', args=[appointment.id]), # Ссылка на редактирование
            'backgroundColor': '#007bff', # Синий цвет для запланированных
            'borderColor': '#007bff'
        })
    return JsonResponse(events, safe=False)