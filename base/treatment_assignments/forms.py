# treatment_assignments/forms.py
from django import forms
from .models import TreatmentAssignment
from patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()

class TreatmentAssignmentForm(forms.ModelForm):
    """
    Форма для создания и редактирования назначений лечения.
    """
    class Meta:
        model = TreatmentAssignment
        fields = [
            'patient', 'assigning_doctor', 
            'treatment_name', 'dosage', 'frequency', 'duration',
            'notes', 'status'
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'assignment_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'treatment_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название препарата или процедуры'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10 мг'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 2 раза в день'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 7 дней'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'assignment_date': 'Дата назначения',
            'treatment_name': 'Название лечения',
            'dosage': 'Дозировка',
            'frequency': 'Частота',
            'duration': 'Длительность',
            'notes': 'Примечания',
            'status': 'Статус',
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        self.content_object = kwargs.pop('content_object', None)
        self.patient_object = kwargs.pop('patient_object', None)
        super().__init__(*args, **kwargs)
        self.fields['patient'].required = False
        
        if self.patient_object:
            self.fields['patient'].initial = self.patient_object
            self.fields['patient'].widget = forms.HiddenInput()

        if self.request_user and not self.instance.pk:
            self.fields['assigning_doctor'].initial = self.request_user

        if self.instance.pk:
            self.fields['patient'].widget = forms.HiddenInput()
            # self.fields['patient'].widget.attrs['readonly'] = True
            # self.fields['patient'].widget.attrs['disabled'] = True
            # Можно оставить поля для доктора и даты редактируемыми или сделать только для чтения по необходимости
            # self.fields['assigning_doctor'].widget.attrs['readonly'] = True
            # self.fields['assigning_doctor'].widget.attrs['disabled'] = True