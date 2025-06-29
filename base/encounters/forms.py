from django import forms
from .models import Encounter

class EncounterForm(forms.ModelForm):
    class Meta:
        model = Encounter
        fields = ['type', 'date_start']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }