from datetime import datetime, timedelta
from django.utils import timezone

from .models import Schedule, AppointmentEvent


def generate_available_slots(start_dt, end_dt, doctor_id=None):
    """
    Генерация свободных слотов по расписанию врача между start_dt и end_dt.
    Если doctor_id не указан или некорректен — по всем врачам.
    """
    if not doctor_id or doctor_id == '__all_free__':
        schedules = Schedule.objects.all()
        booked_slots = set(AppointmentEvent.objects.filter(
            start__range=[start_dt, end_dt]
        ).values_list('start', flat=True))
    else:
        schedules = Schedule.objects.filter(doctor_id=doctor_id)
        booked_slots = set(AppointmentEvent.objects.filter(
            schedule__doctor_id=doctor_id,
            start__range=[start_dt, end_dt]
        ).values_list('start', flat=True))

    available_slots = []

    for schedule in schedules:
        # Переход к наивному времени для RecurrenceField
        # Используем timezone.localtime() для корректного преобразования
        if timezone.is_aware(start_dt):
            start_dt_naive = timezone.localtime(start_dt).replace(tzinfo=None)
        else:
            start_dt_naive = start_dt
            
        if timezone.is_aware(end_dt):
            end_dt_naive = timezone.localtime(end_dt).replace(tzinfo=None)
        else:
            end_dt_naive = end_dt
        
        occurrences = schedule.recurrences.between(
            start_dt_naive,
            end_dt_naive,
            inc=True
        )

        for shift_start_date in occurrences:
            # Создаем datetime в локальной зоне времени
            slot_start_naive = datetime.combine(shift_start_date.date(), schedule.start_time)
            if timezone.is_naive(slot_start_naive):
                current_time = timezone.make_aware(slot_start_naive, timezone.get_current_timezone())
            else:
                current_time = slot_start_naive
                
            end_of_shift_naive = datetime.combine(shift_start_date.date(), schedule.end_time)
            if timezone.is_naive(end_of_shift_naive):
                end_of_shift = timezone.make_aware(end_of_shift_naive, timezone.get_current_timezone())
            else:
                end_of_shift = end_of_shift_naive

            while current_time < end_of_shift:
                if current_time not in booked_slots:
                    # Формируем ФИО врача
                    doctor_name = "Неизвестный врач"
                    if schedule.doctor:
                        if hasattr(schedule.doctor, 'doctor_profile') and schedule.doctor.doctor_profile:
                            full_name = schedule.doctor.doctor_profile.full_name
                        else:
                            full_name = f"{schedule.doctor.last_name} {schedule.doctor.first_name}"
                        
                        # Форматируем в "Фамилия И.О."
                        parts = full_name.split()
                        if len(parts) >= 2:
                            doctor_name = f"{parts[0]} {parts[1][0]}."
                            if len(parts) > 2:
                                doctor_name += f"{parts[2][0]}."
                        else:
                            doctor_name = full_name
                    
                    available_slots.append({
                        "title": doctor_name,
                        "start": current_time.isoformat(),
                        "end": (current_time + timedelta(minutes=schedule.duration)).isoformat(),
                        "color": "#28a745",
                        "extendedProps": {"schedule_id": schedule.id}
                    })
                current_time += timedelta(minutes=schedule.duration)

    return available_slots
