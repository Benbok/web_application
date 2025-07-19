# appointments/forms.py

from django import forms
from django.utils import timezone
from django.forms import ValidationError

from .models import AppointmentEvent
from .models import Schedule
from django.contrib.auth import get_user_model
from django_select2.forms import ModelSelect2Widget
from patients.models import Patient

User = get_user_model()

class AppointmentEventForm(forms.ModelForm):
    class Meta:
        model = AppointmentEvent
        fields = ['schedule', 'patient', 'start', 'notes', 'status']
        widgets = {
            'start': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'patient': ModelSelect2Widget(
                model=Patient,
                search_fields=['last_name__icontains', 'first_name__icontains', 'middle_name__icontains'],
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Если у нас есть начальные данные для поля start, оставляем их в московском времени
        if self.initial and 'start' in self.initial:
            start_time = self.initial['start']
            if hasattr(start_time, 'astimezone'):
                # Оставляем московское время как есть
                self.initial['start'] = start_time.strftime('%Y-%m-%dT%H:%M')

    def prepare_value(self, field_name):
        """Подготавливаем значение для отображения в форме"""
        if field_name == 'start' and self.instance.pk:
            # Для существующих записей оставляем московское время
            start_time = getattr(self.instance, field_name)
            if start_time and hasattr(start_time, 'astimezone'):
                return start_time.strftime('%Y-%m-%dT%H:%M')
        return super().prepare_value(field_name)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        schedule = cleaned_data.get('schedule')
        patient = cleaned_data.get('patient')

        if start and schedule:
            # Убеждаемся, что время в правильной зоне
            if timezone.is_naive(start):
                # Пользователь ввел время в московской зоне
                # Делаем время aware в текущей зоне Django (московской)
                start = timezone.make_aware(start, timezone.get_current_timezone())
                cleaned_data['start'] = start
            
            self.instance.end = start + timezone.timedelta(minutes=schedule.duration)
            end = self.instance.end

            # Проверка, что время приёма в рамках расписания
            schedule_start = schedule.start_time
            schedule_end = schedule.end_time
            if not (schedule_start <= start.time() < schedule_end and schedule_start < end.time() <= schedule_end):
                raise ValidationError("Время приёма выходит за пределы смены врача.")

            # Проверка на пересечение у врача
            doctor = schedule.doctor
            overlapping_doctor = AppointmentEvent.objects.filter(
                schedule__doctor=doctor,
                start__lt=end,
                end__gt=start,
                status='scheduled'
            ).exclude(pk=self.instance.pk)
            if overlapping_doctor.exists():
                raise ValidationError("У выбранного врача уже есть запись в это время.")

            # Проверка на пересечение у пациента
            overlapping_patient = AppointmentEvent.objects.filter(
                patient=patient,
                start__lt=end,
                end__gt=start,
                status='scheduled'
            ).exclude(pk=self.instance.pk)
            if overlapping_patient.exists():
                raise ValidationError("У пациента уже есть запись в это время.")

        return cleaned_data




class ScheduleAdminForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Меняем отображение пользователей в выпадающем списке врачей
        self.fields['doctor'].label_from_instance = lambda obj: (
            obj.doctor_profile.full_name if hasattr(obj, 'doctor_profile') and obj.doctor_profile else obj.username
        )
