# appointments/forms.py
from django import forms
from .models import AppointmentEvent
from .models import Schedule
from django.contrib.auth import get_user_model

User = get_user_model()

class AppointmentEventForm(forms.ModelForm):
    class Meta:
        model = AppointmentEvent
        fields = "__all__"

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
