from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import time, date

from .models import ExaminationLabTest, ExaminationPlan, ExaminationInstrumental
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition
from clinical_scheduling.forms import ScheduleSettingsForm


class ExaminationLabTestForm(forms.ModelForm):
    """Форма для добавления лабораторного исследования в план обследования"""
    
    class Meta:
        model = ExaminationLabTest
        fields = ['lab_test', 'is_active', 'instructions']
        widgets = {
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExaminationLabTestWithScheduleForm(ExaminationLabTestForm):
    """Интегрированная форма для добавления лабораторного исследования с настройкой расписания"""
    
    # Поля для расписания
    start_date = forms.DateField(
        label=_('Дата начала'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        initial=date.today,
        help_text=_('С какой даты начинать расписание')
    )
    
    first_time = forms.TimeField(
        label=_('Время выполнения'),
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(9, 0),
        help_text=_('Время выполнения исследования')
    )
    
    times_per_day = forms.IntegerField(
        label=_('Количество раз в день'),
        min_value=1,
        max_value=24,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('Сколько раз в день выполнять исследование')
    )
    
    duration_days = forms.IntegerField(
        label=_('Длительность курса (дней)'),
        min_value=1,
        max_value=365,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        help_text=_('Лабораторные исследования обычно выполняются один раз')
    )
    
    # Скрытое поле для включения расписания
    enable_schedule = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем readonly для duration_days
        self.fields['duration_days'].widget.attrs['readonly'] = 'readonly'
    
    def clean(self):
        cleaned_data = super().clean()
        times_per_day = cleaned_data.get('times_per_day')
        duration_days = cleaned_data.get('duration_days')
        
        if times_per_day and duration_days:
            if times_per_day * duration_days > 1000:
                raise forms.ValidationError(
                    _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                )
        
        return cleaned_data


class ExaminationInstrumentalForm(forms.ModelForm):
    """Форма для добавления инструментального исследования в план обследования"""
    
    class Meta:
        model = ExaminationInstrumental
        fields = ['instrumental_procedure', 'is_active', 'instructions']
        widgets = {
            'instrumental_procedure': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExaminationInstrumentalWithScheduleForm(ExaminationInstrumentalForm):
    """Интегрированная форма для добавления инструментального исследования с настройкой расписания"""
    
    # Поля для расписания
    start_date = forms.DateField(
        label=_('Дата начала'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        initial=date.today,
        help_text=_('С какой даты начинать расписание')
    )
    
    first_time = forms.TimeField(
        label=_('Время выполнения'),
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(9, 0),
        help_text=_('Время выполнения процедуры')
    )
    
    times_per_day = forms.IntegerField(
        label=_('Количество раз в день'),
        min_value=1,
        max_value=24,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('Сколько раз в день выполнять процедуру')
    )
    
    duration_days = forms.IntegerField(
        label=_('Длительность курса (дней)'),
        min_value=1,
        max_value=365,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        help_text=_('Процедуры обычно выполняются один раз')
    )
    
    # Скрытое поле для включения расписания
    enable_schedule = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем readonly для duration_days
        self.fields['duration_days'].widget.attrs['readonly'] = 'readonly'
    
    def clean(self):
        cleaned_data = super().clean()
        times_per_day = cleaned_data.get('times_per_day')
        duration_days = cleaned_data.get('duration_days')
        
        if times_per_day and duration_days:
            if times_per_day * duration_days > 1000:
                raise forms.ValidationError(
                    _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                )
        
        return cleaned_data


class ExaminationPlanForm(forms.ModelForm):
    """Форма для создания плана обследования"""
    
    class Meta:
        model = ExaminationPlan
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        } 