from django import forms
from .models import NewbornProfile

class NewbornProfileForm(forms.ModelForm):
    class Meta:
        model = NewbornProfile
        fields = [
            'birth_time',
            'gestational_age_weeks',
            'gestational_age_days',
            'birth_weight_grams',
            'birth_height_cm',
            'head_circumference_cm',
            'apgar_score_1_min',
            'apgar_score_5_min',
            'apgar_score_10_min',
            'notes',
            'obstetric_history',
            'physical_development'
        ]
        widgets = {
            'birth_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'gestational_age_weeks': forms.NumberInput(attrs={'class': 'form-control'}),
            'gestational_age_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_weight_grams': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_height_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'head_circumference_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'apgar_score_1_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'apgar_score_5_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'apgar_score_10_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'obstetric_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'physical_development': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'readonly': True}),
        }
