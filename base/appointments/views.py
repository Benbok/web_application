# appointments/views.py
import json

from rest_framework import viewsets
from django.http import JsonResponse
from django.views.generic import TemplateView, CreateView, UpdateView, View, DetailView, DeleteView
from django.urls import reverse_lazy
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, time, timedelta
from django.utils.dateparse import parse_datetime
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .services import generate_available_slots
from django.views.decorators.csrf import csrf_exempt
from encounters.models import Encounter
from django.shortcuts import get_object_or_404, redirect

from .models import Schedule, AppointmentEvent
from .serializers import AppointmentEventSerializer
from .forms import AppointmentEventForm

User = get_user_model()

class AppointmentEventViewSet(viewsets.ModelViewSet):
    queryset = AppointmentEvent.objects.all()
    serializer_class = AppointmentEventSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        doctor_id = self.request.query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(schedule__doctor__id=doctor_id)
        return queryset


class AppointmentEventsAPI(View):
    """
    API для FullCalendar. Возвращает ЗАПИСАННЫЕ приемы.
    """

    def get(self, request, *args, **kwargs):
        appointments = AppointmentEvent.objects.select_related(
            'patient',
            'schedule__doctor'
        ).filter(status="scheduled")

        events = []
        for appt in appointments:
            if not appt.schedule or not appt.schedule.doctor:
                continue
            # Формируем Фамилия И.О.
            if hasattr(appt.patient, 'full_name') and appt.patient.full_name:
                parts = appt.patient.full_name.split()
                if len(parts) >= 2:
                    fio = f"{parts[0]} {parts[1][0]}."
                    if len(parts) > 2:
                        fio += f"{parts[2][0]}."
                else:
                    fio = appt.patient.full_name
            else:
                fio = str(appt.patient)
            events.append({
                'title': fio,
                'start': appt.start.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': appt.end.strftime('%Y-%m-%dT%H:%M:%S'),
                'color': '#dc3545',
                'textColor': 'white',
                'id': appt.id
            })
            
        return JsonResponse(events, safe=False)


class AvailableSlotsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        doctor_id = request.query_params.get('doctor_id')

        if not all([start_str, end_str, doctor_id]):
            return Response({"error": "Необходимы параметры start, end и doctor_id"}, status=400)

        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

        slots = generate_available_slots(start_dt, end_dt, doctor_id)
        return Response(slots)
class CalendarView(TemplateView):
    template_name = "appointments/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['doctors'] = User.objects.only('id', 'first_name', 'last_name').filter(doctor_profile__isnull=False)
        return context


class AppointmentCreateView(CreateView):
    model = AppointmentEvent
    form_class = AppointmentEventForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')

    def get_initial(self):
        initial = super().get_initial()

        # ✅ Попытка прочитать параметры из сессии (после создания пациента)
        params = self.request.session.pop('appointment_params', None)
        if params:
            initial['schedule'] = params.get('schedule')
            start = params.get('start')
            if start:
                parsed_start = parse_datetime(start)
                if parsed_start:
                    initial['start'] = parsed_start

        # ✅ Попытка прочитать параметры из URL (при первом заходе)
        if 'schedule' not in initial:
            schedule_id = self.request.GET.get('schedule_id')
            start = self.request.GET.get('start')
            if schedule_id:
                initial['schedule'] = schedule_id
            if start:
                parsed_start = parse_datetime(start)
                if parsed_start:
                    initial['start'] = parsed_start

        # ✅ Отдельно читаем patient_id (из URL после создания пациента)
        patient_id = self.request.GET.get('patient_id')
        if patient_id:
            initial['patient'] = patient_id

        return initial


class AppointmentUpdateView(UpdateView):
    model = AppointmentEvent
    form_class = AppointmentEventForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:calendar')


class AppointmentEventUpdateView(UpdateView):
    model = AppointmentEvent
    form_class = AppointmentEventForm
    template_name = 'appointments/appointment_form.html'

    def get_success_url(self):
        return reverse_lazy('appointments:detail', kwargs={'pk': self.object.pk})

class AppointmentEventDetailView(DetailView):
    model = AppointmentEvent
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'

class AppointmentEventDeleteView(DeleteView):
    model = AppointmentEvent
    template_name = 'appointments/appointment_confirm_delete.html'
    success_url = reverse_lazy('appointments:calendar')

@csrf_exempt
def save_session_params(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        request.session['appointment_params'] = data
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'invalid method'}, status=405)

class CreateEncounterForAppointmentView(View):
    def post(self, request, pk):
        appointment = get_object_or_404(AppointmentEvent, pk=pk)
        if appointment.encounter:
            return redirect('encounters:encounter_detail', pk=appointment.encounter.pk)
        # Создаём Encounter
        encounter = Encounter.objects.create(
            patient=appointment.patient,
            doctor=appointment.schedule.doctor if appointment.schedule else None,
            date_start=appointment.start,
        )
        appointment.encounter = encounter
        appointment.save()
        return redirect('encounters:encounter_detail', pk=encounter.pk)

