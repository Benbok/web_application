# appointments/views.py
from rest_framework import viewsets
from django.http import JsonResponse
from django.views.generic import TemplateView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, time, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

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
            queryset = queryset.filter(doctor_id=doctor_id)
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

            events.append({
                'title': f"{appt.patient.full_name} -> Dr. {appt.schedule.doctor.last_name}",
                # Use strftime to avoid timezone issues on the front-end
                'start': appt.start.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': appt.end.strftime('%Y-%m-%dT%H:%M:%S'),
                'color': '#dc3545',
                'textColor': 'white',
                'id': appt.id
            })
        return JsonResponse(events, safe=False)


class AvailableSlotsAPIView(APIView):
    """
    Генерирует и возвращает список свободных слотов для записи.
    """

    def get(self, request, *args, **kwargs):
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        doctor_id = request.query_params.get('doctor_id')

        if not all([start_str, end_str, doctor_id]):
            return Response({"error": "Необходимы параметры start, end и doctor_id"}, status=400)

        # 1. Получаем "осведомленные" datetime из запроса
        start_dt_aware = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt_aware = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

        schedules = Schedule.objects.filter(doctor_id=doctor_id)

        # Занятые слоты получаем, используя "осведомленные" даты
        booked_slots = set(AppointmentEvent.objects.filter(
            schedule__doctor_id=doctor_id,
            start__range=[start_dt_aware, end_dt_aware],
            status="scheduled"
        ).values_list('start', flat=True))

        available_slots = []
        for schedule in schedules:
            # --- ОСНОВНОЕ ИСПРАВЛЕНИЕ ---
            # 2. Передаем в метод .between() "НАИВНЫЕ" версии дат.
            # Мы просто "отрезаем" информацию о часовом поясе.
            occurrences = schedule.recurrences.between(
                start_dt_aware.replace(tzinfo=None),
                end_dt_aware.replace(tzinfo=None),
                inc=True
            )
            # ---------------------------

            for shift_start_date in occurrences:
                # Генерируем "талоны" внутри одной смены
                slot_start_naive = datetime.combine(shift_start_date.date(), schedule.start_time)
                current_time = timezone.make_aware(
                    slot_start_naive)  # Делаем их "осведомленными" для дальнейших сравнений

                end_of_shift_naive = datetime.combine(shift_start_date.date(), schedule.end_time)
                end_of_shift = timezone.make_aware(end_of_shift_naive)

                while current_time < end_of_shift:
                    if current_time not in booked_slots:
                        available_slots.append({
                            "title": "Свободно",
                            "start": current_time.isoformat(),
                            "end": (current_time + timedelta(minutes=schedule.duration)).isoformat(),
                            "color": "#28a745",
                            "extendedProps": {"schedule_id": schedule.id}
                        })
                    current_time += timedelta(minutes=schedule.duration)

        return Response(available_slots)
class CalendarView(TemplateView):
    template_name = "appointments/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 2. Находим всех пользователей, у которых есть профиль врача
        context['doctors'] = User.objects.filter(doctor_profile__isnull=False)

        # Эту строку можно оставить, если она вам нужна для других целей
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
