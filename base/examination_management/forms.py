from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ExaminationPlan, ExaminationLabTest, ExaminationInstrumental
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition


class ExaminationPlanForm(forms.ModelForm):
    """
    Форма для создания/редактирования плана обследования
    """
    class Meta:
        model = ExaminationPlan
        fields = ['name', 'description', 'priority', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Введите название плана обследования')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Описание плана обследования (необязательно)')
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': _('Название плана'),
            'description': _('Описание'),
            'priority': _('Приоритет'),
            'is_active': _('Активен')
        }


class ExaminationLabTestForm(forms.ModelForm):
    """
    Форма для добавления/редактирования лабораторного исследования в плане
    """
    lab_test = forms.ModelChoiceField(
        queryset=LabTestDefinition.objects.all(),
        label=_('Лабораторное исследование'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ExaminationLabTest
        fields = ['is_active', 'instructions']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Особые указания по исследованию')
            })
        }
        labels = {
            'is_active': _('Активно'),
            'instructions': _('Особые указания')
        }


class ExaminationInstrumentalForm(forms.ModelForm):
    """
    Форма для добавления/редактирования инструментального исследования в плане
    """
    instrumental_procedure = forms.ModelChoiceField(
        queryset=InstrumentalProcedureDefinition.objects.all(),
        label=_('Инструментальное исследование'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ExaminationInstrumental
        fields = ['is_active', 'instructions']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Особые указания по процедуре')
            })
        }
        labels = {
            'is_active': _('Активно'),
            'instructions': _('Особые указания')
        } 