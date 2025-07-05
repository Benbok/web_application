from django import forms
from .models import NewbornProfile

class NewbornProfileForm(forms.ModelForm):
    class Meta:
        model = NewbornProfile
        fields = [
            'gestational_age_weeks',
            'birth_weight_grams',
            'birth_height_cm',
            'head_circumference_cm',
            'apgar_score_1_min',
            'apgar_score_5_min',
            'notes',
        ]
        widgets = {
            'birth_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'gestational_age_weeks': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_weight_grams': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_height_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'head_circumference_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'apgar_score_1_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'apgar_score_5_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
