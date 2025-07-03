# treatment_assignments/forms.py
from django import forms
from .models import TreatmentAssignment
from patients.models import Patient
from pharmacy.models import Medication # Импортируем модель Medication
from django.contrib.auth import get_user_model
from django_select2.forms import Select2Widget # Импортируем Select2Widget

User = get_user_model()

class TreatmentAssignmentForm(forms.ModelForm):
    calculated_dosage = forms.CharField(
        label="Расчетная дозировка",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    dosage_per_kg = forms.DecimalField(
        label="Дозировка на кг",
        required=False,
        max_digits=10,
        decimal_places=3,   
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10'})
    )
    default_dosage_per_kg_unit_display = forms.CharField(
        label="Единица дозировки на кг (по умолчанию)",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    class Meta:
        model = TreatmentAssignment
        fields = [
            'patient', 'assigning_doctor', 'patient_weight',
            'medication', 'frequency', 'duration', 'route', # Removed 'dosage'
            'notes', 'status', 'start_date',
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'patient_weight': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10.5', 'step': '0.1'}),
            'dosage_per_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10', 'step': '0.1'}),
            'assignment_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'medication': Select2Widget(attrs={'class': 'form-select'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 2 раза в день'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 7 дней'}),
            'route': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, внутримышечно'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'patient_weight': 'Вес пациента (кг)',
            'assignment_date': 'Дата назначения',
            'medication': 'Препарат',
            'frequency': 'Частота',
            'duration': 'Длительность',
            'route': 'Путь введения',
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

        # Устанавливаем поля отображения как disabled
        self.fields['calculated_dosage'].disabled = True
        self.fields['default_dosage_per_kg_unit_display'].disabled = True

        # Если форма не отправлена (GET-запрос) и есть выбранный препарат,
        # заполняем поля дозировки, частоты и длительности из Medication.
        if not self.data and self.instance.medication:
            medication = self.instance.medication
            # self.fields['dosage'].initial = medication.default_dosage # Removed
            self.fields['frequency'].initial = medication.default_frequency
            self.fields['duration'].initial = medication.default_duration
            self.fields['route'].initial = medication.default_route

            # Заполняем поле dosage_per_kg из default_dosage_per_kg
            if medication.default_dosage_per_kg:
                self.fields['dosage_per_kg'].initial = medication.default_dosage_per_kg
            
            # Заполняем расчетную дозировку при загрузке формы
            if medication.default_dosage_per_kg and self.instance.patient_weight:
                calculated_val = medication.default_dosage_per_kg * self.instance.patient_weight
                self.fields['calculated_dosage'].initial = f"{calculated_val:.2f} {medication.default_dosage_per_kg_unit or ''}"
            elif medication.default_dosage: # Если нет дозировки на кг, используем обычную дозировку
                self.fields['calculated_dosage'].initial = medication.default_dosage
            
            # Заполняем поля отображения
            self.fields['default_dosage_per_kg_unit_display'].initial = medication.default_dosage_per_kg_unit

        # Если форма отправлена (POST-запрос) и выбран препарат,
        # но поля дозировки, частоты и длительности не заполнены,
        # заполняем их из Medication.
        if self.data and 'medication' in self.data and not self.instance.pk:
            try:
                medication_id = self.data.get('medication')
                medication = Medication.objects.get(pk=medication_id)
                # if not self.data.get('dosage'): # Removed
                #     self.fields['dosage'].initial = medication.default_dosage
                if not self.data.get('frequency'):
                    self.fields['frequency'].initial = medication.default_frequency
                if not self.data.get('duration'):
                    self.fields['duration'].initial = medication.default_duration
                if not self.data.get('route'):
                    self.fields['route'].initial = medication.default_route
            except Medication.DoesNotExist:
                pass
