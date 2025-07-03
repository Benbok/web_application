# treatment_assignments/forms.py
from django import forms
from .models import MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment, InstrumentalProcedureAssignment
from pharmacy.models import Medication
from django.contrib.auth import get_user_model
from django_select2.forms import Select2Widget
from django.utils import timezone

User = get_user_model()

# Базовая форма для всех типов назначений
class BaseAssignmentForm(forms.ModelForm):
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

    def save(self, commit=True):
        """
        Переопределяем метод сохранения для добавления кастомной логики
        для статуса и даты завершения.
        """
        # Сначала получаем объект модели, но пока не сохраняем его в базу данных.
        instance = super().save(commit=False)

        # Получаем значения из проверенных данных формы.
        status = self.cleaned_data.get('status')
        end_date = self.cleaned_data.get('end_date')

        # ЛОГИКА 1: Если пользователь установил статус "Завершено",
        # а дату завершения оставил пустой, то устанавливаем текущее время.
        if status == 'active':
            instance.end_date = None

            # ПРАВИЛО 2: Если статус НЕ "Активно" и пользователь указал дату завершения,
            # то мы принудительно устанавливаем статус "Завершено".
        elif end_date:
            instance.status = 'completed'

            # ПРАВИЛО 3 (на всякий случай): Если пользователь выбрал "Завершено",
            # но не указал дату, подставим текущую.
        elif status == 'completed':
            # instance.end_date тут будет пустым, т.к. мы прошли проверку 'elif end_date'
            instance.end_date = timezone.now()


        # Если commit=True, сохраняем измененный объект в базу данных.
        if commit:
            instance.save()
            # Django требует сохранить и m2m поля после основного сохранения.
            self.save_m2m()

        return instance

class MedicationAssignmentForm(BaseAssignmentForm):
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
        model = MedicationAssignment
        fields = [
            'patient', 'assigning_doctor', 'patient_weight',
            'medication', 'frequency', 'duration', 'route',
            'notes', 'status', 'start_date', 'end_date',
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'patient_weight': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10.5', 'step': '0.1'}),
            'dosage_per_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10', 'step': '0.1'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'medication': Select2Widget(attrs={'class': 'form-select'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 2 раза в день'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, 7 дней'}),
            'route': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, внутримышечно'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'patient_weight': 'Вес пациента (кг)',
            'start_date': 'Дата назначения',
            'medication': 'Препарат',
            'frequency': 'Частота',
            'duration': 'Длительность',
            'route': 'Путь введения',
            'notes': 'Примечания',
            'status': 'Статус',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем поля отображения как disabled
        self.fields['calculated_dosage'].disabled = True
        self.fields['default_dosage_per_kg_unit_display'].disabled = True

        # Если форма не отправлена (GET-запрос) и это существующий объект (для редактирования),
        # заполняем поля дозировки, частоты и длительности из Medication.
        if not self.data and self.instance.pk and self.instance.medication:
            medication = self.instance.medication
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
                if not self.data.get('frequency'):
                    self.fields['frequency'].initial = medication.default_frequency
                if not self.data.get('duration'):
                    self.fields['duration'].initial = medication.default_duration
                if not self.data.get('route'):
                    self.fields['route'].initial = medication.default_route
            except Medication.DoesNotExist:
                pass


class GeneralTreatmentAssignmentForm(BaseAssignmentForm):
    class Meta:
        model = GeneralTreatmentAssignment
        fields = [
            'patient', 'assigning_doctor', 'general_treatment',
            'notes', 'status', 'start_date', 'end_date',
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'general_treatment': Select2Widget(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'general_treatment': 'Общее назначение',
            'notes': 'Примечания',
            'status': 'Статус',
            'start_date': 'Дата начала',
            'end_date': 'Дата завершения',
        }


class LabTestAssignmentForm(BaseAssignmentForm):
    class Meta:
        model = LabTestAssignment
        fields = [
            'patient', 'assigning_doctor', 'lab_test',
            'notes', 'status', 'start_date', 'end_date',
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'lab_test': Select2Widget(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'lab_test': 'Лабораторное исследование',
            'notes': 'Примечания',
            'status': 'Статус',
            'start_date': 'Дата начала',
            'end_date': 'Дата завершения',
        }


class InstrumentalProcedureAssignmentForm(BaseAssignmentForm):
    class Meta:
        model = InstrumentalProcedureAssignment
        fields = [
            'patient', 'assigning_doctor', 'instrumental_procedure',
            'notes', 'status', 'start_date', 'end_date',
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'instrumental_procedure': Select2Widget(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'instrumental_procedure': 'Инструментальное исследование',
            'notes': 'Примечания',
            'status': 'Статус',
            'start_date': 'Дата начала',
            'end_date': 'Дата завершения',
        }
