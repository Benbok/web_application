# appointments/forms.py
from django import forms
from .models import AppointmentEvent

class AppointmentEventForm(forms.ModelForm):
    class Meta:
        model = AppointmentEvent
        fields = [
            'doctor',
            'patient',
            'start',
            'end',
            'notes',
            'status',
            'recurrence',
        ]
        widgets = {
            'start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'recurrence': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }