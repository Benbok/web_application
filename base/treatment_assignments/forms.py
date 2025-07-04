# treatment_assignments/forms.py
from django import forms
from .models import MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment, InstrumentalProcedureAssignment, BaseAssignment
from instrumental_procedures.models import InstrumentalProcedureResult
from pharmacy.models import Medication
from django.contrib.auth import get_user_model
from django_select2.forms import Select2Widget
from django.utils import timezone
from pharmacy.models import DosingRule, Medication

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

        self.fields['cancellation_reason'].widget = forms.Textarea(attrs={'rows': 2, 'style': 'display:none;'})
        self.fields['cancellation_reason'].required = False

        # Добавляем поле completed_by и делаем его неактивным по умолчанию
        self.fields['completed_by'].widget = forms.Select(attrs={'class': 'form-select'})
        self.fields['completed_by'].required = False
        self.fields['completed_by'].disabled = True # По умолчанию поле неактивно

    def save(self, commit=True):
        """
        Переопределяем метод сохранения для добавления кастомной логики
        для статуса и даты завершения.
        """
        # Сначала получаем объект модели, но пока не сохраняем его в базу данных.
        instance = super().save(commit=False)

        # Получаем значения из проверенных данных формы.
        status = self.cleaned_data.get('status')

        # Если статус меняется на 'completed', устанавливаем completed_by
        if status == 'completed' and not instance.completed_by:
            instance.completed_by = self.request_user
        elif status != 'completed' and instance.completed_by:
            # Если статус не 'completed', но completed_by уже установлен, сбрасываем его
            instance.completed_by = None

        # Логика для InstrumentalProcedureAssignment
        if isinstance(instance, InstrumentalProcedureAssignment):
            if status == 'completed':
                # Пытаемся получить последний результат для этого назначения
                latest_result = InstrumentalProcedureResult.objects.filter(
                    instrumental_procedure_assignment=instance
                ).order_by('-datetime_result').first()
                if latest_result:
                    instance.end_date = latest_result.datetime_result
                else:
                    # Если результата нет, но статус завершен, ставим текущее время
                    instance.end_date = timezone.now()
            elif status == 'active' or status == 'paused':
                instance.end_date = None
            elif status == 'canceled':
                instance.end_date = timezone.now()
                if not self.cleaned_data.get('cancellation_reason'):
                    self.add_error('cancellation_reason', 'Пожалуйста, укажите причину отмены.')
        else:
            # Общая логика для других типов назначений
            if status == 'canceled':
                instance.end_date = timezone.now()
                if not self.cleaned_data.get('cancellation_reason'):
                    self.add_error('cancellation_reason', 'Пожалуйста, укажите причину отмены.')
            elif status == 'paused' or status == 'active':
                instance.end_date = None
            elif status == 'completed':
                # Если статус завершен, но дата не указана, ставим текущее время
                if not self.cleaned_data.get('end_date'):
                    instance.end_date = timezone.now()

        # Если commit=True, сохраняем измененный объект в базу данных.
        if commit:
            instance.save()
            # Django требует сохранить и m2m поля после основного сохранения.
            self.save_m2m()

        return instance

class MedicationAssignmentForm(BaseAssignmentForm):

    dosing_rule = forms.ModelChoiceField(
        queryset=DosingRule.objects.none(),  # Изначально queryset пустой
        label="Правило дозирования",
        required=False
    )

    class Meta:
        model = MedicationAssignment
        fields = [
            'patient', 'start_date', 'end_date', 'status', 'notes',
            'assigning_doctor', 'cancellation_reason', 'completed_by',
            'medication',
            'dosing_rule', 'duration_days',
            'patient_weight',
        ]

        widgets = {
            'patient': forms.HiddenInput(),
            'assigning_doctor': forms.Select(attrs={'class': 'form-select'}),
            'patient_weight': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 10.5', 'step': '0.1'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'medication': Select2Widget(attrs={'class': 'form-select'}),
            'dosing_rule': Select2Widget(attrs={'class': 'form-select'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Например, 7'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительные примечания'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'patient': 'Пациент',
            'assigning_doctor': 'Назначивший врач',
            'patient_weight': 'Вес пациента (кг)',
            'start_date': 'Дата назначения',
            'medication': 'Препарат',
            'dosing_rule': 'Правило дозирования',
            'notes': 'Примечания',
            'status': 'Статус',
            'end_date': 'Дата завершения',
            'completed_by': 'Завершено кем',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter dosing rules based on selected medication
        if 'medication' in self.initial:
            medication_id = self.initial['medication']
            self.fields['dosing_rule'].queryset = self.fields['dosing_rule'].queryset.filter(medication_id=medication_id)
        elif self.instance.pk and self.instance.medication:
            self.fields['dosing_rule'].queryset = self.fields['dosing_rule'].queryset.filter(medication=self.instance.medication)
        else:
            self.fields['dosing_rule'].queryset = self.fields['dosing_rule'].queryset.none()

        # Add JavaScript for dynamic filtering of dosing rules
        self.fields['medication'].widget.attrs['onchange'] = 'updateDosingRules(this);'

        # If form is submitted (POST request) and medication is selected,
        # filter dosing rules based on medication.
        if self.data and 'medication' in self.data:
            try:
                medication_id = self.data.get('medication')
                self.fields['dosing_rule'].queryset = self.fields['dosing_rule'].queryset.filter(medication_id=medication_id)
            except Medication.DoesNotExist:
                pass


class GeneralTreatmentAssignmentForm(BaseAssignmentForm):
    class Meta:
        model = GeneralTreatmentAssignment
        fields = [
            'patient', 'assigning_doctor', 'general_treatment',
            'notes', 'status', 'start_date', 'end_date', 'cancellation_reason', 'completed_by',
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
            'completed_by': 'Завершено кем',
        }


class LabTestAssignmentForm(BaseAssignmentForm):
    class Meta:
        model = LabTestAssignment
        fields = [
            'patient', 'assigning_doctor', 'lab_test',
            'notes', 'status', 'start_date', 'end_date', 'cancellation_reason', 'completed_by',
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
            'completed_by': 'Завершено кем',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['end_date'].disabled = True


class InstrumentalProcedureAssignmentForm(BaseAssignmentForm):
    class Meta:
        model = InstrumentalProcedureAssignment
        fields = [
            'patient', 'assigning_doctor', 'instrumental_procedure',
            'notes', 'status', 'start_date', 'end_date', 'cancellation_reason', 'completed_by',
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
            'completed_by': 'Завершено кем',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['end_date'].disabled = True
