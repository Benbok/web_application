from django import forms
from .models import Patient, PatientContact, PatientAddress, PatientDocument
from newborns.models import NewbornProfile

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'last_name', 'first_name', 'middle_name', 'birth_date',
            'gender'  # здесь только то, что реально в Patient
        ]
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }


class NewbornPatientForm(forms.ModelForm):
    """
    Урезанная форма Patient, ТОЛЬКО для данных самого ребенка.
    """
    class Meta:
        model = Patient
        fields = ['last_name', 'first_name', 'middle_name', 'birth_date', 'gender']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'last_name': 'Фамилия ребенка',
            'first_name': 'Имя',
            'middle_name': 'Отчество (если есть)',
            'birth_date': 'Дата и время рождения',
            'gender': 'Пол',
        }

class PatientContactForm(forms.ModelForm):
    class Meta:
        model = PatientContact
        exclude = ['patient']

class PatientAddressForm(forms.ModelForm):
    class Meta:
        model = PatientAddress
        exclude = ['patient']

class PatientDocumentForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        exclude = ['patient']

        widgets = {
            'passport_issued_date': forms.DateInput(attrs={'type': 'date'}),
        }

class NewbornProfileForm(forms.ModelForm):
    """
    Форма для специфических данных новорожденного из модели NewbornProfile.
    """
    class Meta:
        model = NewbornProfile
        # Исключаем поля, которые будут установлены автоматически
        exclude = ['patient', 'mother']
        widgets = {
            'gestational_age_weeks': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_weight_grams': forms.NumberInput(attrs={'class': 'form-control'}),
            'birth_height_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'head_circumference_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'apgar_score_1_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'apgar_score_5_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }