# appointments/forms.py
from django import forms
from .models import AppointmentEvent

class AppointmentEventForm(forms.ModelForm):
    class Meta:
        model = AppointmentEvent
        fields = "__all__"