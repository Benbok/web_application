from django import forms
from .models import Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            # Основные данные
            'last_name', 'first_name', 'middle_name', 'birth_date', 'gender',

            # Паспортные данные
            'passport_series', 'passport_number', 'passport_issued_by',
            'passport_issued_date', 'passport_department_code',

            # Идентификация
            'snils', 'insurance_policy_number', 'insurance_company',

            # Адреса и контакты
            'registration_address', 'residential_address', 'phone', 'email',

            # Представитель
            'legal_representative_full_name', 'legal_representative_relation', 'legal_representative_contacts'
        ]

        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'passport_issued_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'placeholder': '+7 (___) ___-__-__', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@example.com', 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_series': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_issued_by': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_department_code': forms.TextInput(attrs={'class': 'form-control'}),
            'snils': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_policy_number': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_company': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'legal_representative_full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_representative_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_representative_contacts': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if last_name:
            return ' '.join(word.capitalize() for word in last_name.strip().split())
        return last_name

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            return ' '.join(word.capitalize() for word in first_name.strip().split())
        return first_name

    def clean_middle_name(self):
        middle_name = self.cleaned_data.get('middle_name')
        if middle_name:
            return ' '.join(word.capitalize() for word in middle_name.strip().split())
        return middle_name
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            return ''.join(filter(str.isdigit, phone))
        return phone
