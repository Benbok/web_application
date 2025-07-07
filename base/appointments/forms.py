# appointments/forms.py
from django import forms
from django.utils import timezone
from datetime import timedelta  # <-- Импортируем timedelta
from django.contrib.auth import get_user_model
from .models import Appointment, Schedule

User = get_user_model()


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        # УБИРАЕМ 'end_datetime' ИЗ СПИСКА ПОЛЕЙ
        fields = ['patient', 'doctor', 'start_datetime', 'notes']
        widgets = {
            # УБИРАЕМ виджет для 'end_datetime'
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = User.objects.filter(
            doctor_profile__isnull=False,
            is_active=True
        )
        self.fields['start_datetime'].input_formats = ('%Y-%m-%dT%H:%M',)
        # УБИРАЕМ настройку для 'end_datetime'

    def clean(self):
        """
        Переписываем валидацию с учетом автоматического расчета времени.
        """
        cleaned_data = super().clean()
        start = cleaned_data.get('start_datetime')
        doctor = cleaned_data.get('doctor')

        if not (start and doctor):
            return cleaned_data

        if start < timezone.now():
            raise forms.ValidationError("Нельзя записаться на прием в прошлом.")

        # --- Логика расчета и проверки ---
        day_of_week = start.weekday()
        start_time = start.time()

        try:
            schedule = Schedule.objects.get(doctor=doctor, day_of_week=day_of_week)

            # Рассчитываем время окончания
            duration = timedelta(minutes=schedule.appointment_duration)
            end = start + duration

            # Проверяем, попадает ли прием в рабочие часы
            if not (schedule.start_time <= start_time and end.time() <= schedule.end_time):
                raise forms.ValidationError(
                    f"Время приема выходит за рамки рабочего графика врача ({schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')}).")

            # Сохраняем рассчитанное время для использования в методе save()
            cleaned_data['end_datetime'] = end

            # Проверка наложения записей
            conflicting_appointments = Appointment.objects.filter(
                doctor=doctor,
                start_datetime__lt=end,
                end_datetime__gt=start
            ).exclude(pk=self.instance.pk)

            if conflicting_appointments.exists():
                raise forms.ValidationError("Это время уже занято. Пожалуйста, выберите другое.")

        except Schedule.DoesNotExist:
            raise forms.ValidationError("Врач не работает в этот день недели.")

        return cleaned_data

    def save(self, commit=True):
        """
        Переопределяем метод save, чтобы установить рассчитанное время окончания.
        """
        # Устанавливаем рассчитанное значение в экземпляр модели
        self.instance.end_datetime = self.cleaned_data['end_datetime']
        # Вызываем родительский метод save для сохранения объекта в БД
        return super().save(commit)