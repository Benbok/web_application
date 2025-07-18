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
            'start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'patient': ModelSelect2Widget(
                model=Patient,
                search_fields=['last_name__icontains', 'first_name__icontains', 'middle_name__icontains'],
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        schedule = cleaned_data.get('schedule')
        patient = cleaned_data.get('patient')

        if start and schedule:
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
