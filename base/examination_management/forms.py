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
        fields = ['name', 'description', 'priority', 'is_active', 'patient_department_status', 'encounter', 'created_by']
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
            }),
            'patient_department_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'encounter': forms.Select(attrs={
                'class': 'form-select'
            }),
            'created_by': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'name': _('Название плана'),
            'description': _('Описание'),
            'priority': _('Приоритет'),
            'is_active': _('Активен'),
            'patient_department_status': _('Статус пациента в отделении'),
            'encounter': _('Случай обращения'),
            'created_by': _('Создатель плана')
        }
    
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        owner_type = kwargs.pop('owner_type', None)
        owner_id = kwargs.pop('owner_id', None)
        super().__init__(*args, **kwargs)
        
        # Скрываем поля владельца, если они переданы
        if owner_type and owner_id:
            if owner_type == 'department':
                self.fields['patient_department_status'].initial = owner_id
                self.fields['encounter'].widget = forms.HiddenInput()
                self.fields['created_by'].widget = forms.HiddenInput()
            elif owner_type == 'encounter':
                self.fields['encounter'].initial = owner_id
                self.fields['patient_department_status'].widget = forms.HiddenInput()
                self.fields['created_by'].widget = forms.HiddenInput()
        
        # Делаем поля владельца необязательными для редактирования
        if self.instance.pk:
            self.fields['patient_department_status'].required = False
            self.fields['encounter'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        # Устанавливаем owner для валидации (для обратной совместимости)
        if self.owner:
            self.instance.owner = self.owner
        return cleaned_data


class ExaminationLabTestForm(forms.ModelForm):
    """
    Форма для добавления/редактирования лабораторного исследования в плане
    """
    class Meta:
        model = ExaminationLabTest
        fields = ['lab_test', 'is_active', 'instructions']
        widgets = {
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
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
            'lab_test': _('Лабораторное исследование'),
            'is_active': _('Активно'),
            'instructions': _('Особые указания')
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lab_test'].queryset = LabTestDefinition.objects.all()


class ExaminationInstrumentalForm(forms.ModelForm):
    """
    Форма для добавления/редактирования инструментального исследования в плане
    """
    class Meta:
        model = ExaminationInstrumental
        fields = ['instrumental_procedure', 'is_active', 'instructions']
        widgets = {
            'instrumental_procedure': forms.Select(attrs={'class': 'form-select'}),
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
            'instrumental_procedure': _('Инструментальное исследование'),
            'is_active': _('Активно'),
            'instructions': _('Особые указания')
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instrumental_procedure'].queryset = InstrumentalProcedureDefinition.objects.all() 