from datetime import datetime, timedelta
from django.utils import timezone

from .models import Schedule, AppointmentEvent


def generate_available_slots(start_dt, end_dt, doctor_id):
    """
    Генерация свободных слотов по расписанию врача между start_dt и end_dt.
    """
    schedules = Schedule.objects.filter(doctor_id=doctor_id)

    booked_slots = set(AppointmentEvent.objects.filter(
        schedule__doctor_id=doctor_id,
        start__range=[start_dt, end_dt]
    ).values_list('start', flat=True))

    available_slots = []

    for schedule in schedules:
        # Переход к наивному времени для RecurrenceField
        occurrences = schedule.recurrences.between(
            start_dt.replace(tzinfo=None),
            end_dt.replace(tzinfo=None),
            inc=True
        )

        for shift_start_date in occurrences:
            slot_start_naive = datetime.combine(shift_start_date.date(), schedule.start_time)
            current_time = timezone.make_aware(slot_start_naive)
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

    return available_slots
