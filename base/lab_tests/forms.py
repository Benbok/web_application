from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import LabTestResult

FIELD_TYPE_MAP = {
    'text': forms.CharField,
    'textarea': lambda **kwargs: forms.CharField(widget=forms.Textarea, **kwargs),
    'number': forms.IntegerField,
    'decimal': forms.DecimalField,
    'date': forms.DateField,
    'datetime': forms.DateTimeField,
    'checkbox': forms.BooleanField,
    'choice': forms.ChoiceField,
}

def build_lab_test_result_form(schema, user=None, initial=None):
    """
    Динамически создает класс Django-формы на основе JSON-схемы для результатов лабораторных исследований.
    """
    fields = {
        'datetime_result': forms.DateTimeField(
            label="Дата и время результата",
            widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
        ),
    }
    
    if schema:
        for field_data in schema.get('fields', []):
            field_name = field_data.get('name')
            field_type = field_data.get('type')
            field_label = field_data.get('label', field_name)
            is_required = field_data.get('required', False)

            if not field_name or not field_type:
                continue

            form_field_class = FIELD_TYPE_MAP.get(field_type)
            if not form_field_class:
                continue

            field_kwargs = {
                'label': field_label,
                'required': is_required,
            }

            if field_type == 'choice':
                field_kwargs['choices'] = [(opt, opt) for opt in field_data.get('options', [])]

            if field_name == 'doctor' and user:
                field_kwargs['initial'] = user.get_full_name() or user.username
                field_kwargs['widget'] = forms.TextInput(attrs={'readonly': 'readonly'})

            fields[field_name] = form_field_class(**field_kwargs)

    DynamicLabTestResultForm = type('DynamicLabTestResultForm', (forms.Form,), fields)

    class BaseForm(DynamicLabTestResultForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if initial:
                for key, value in initial.items():
                    if key in self.fields:
                        self.fields[key].initial = value

    return BaseForm

class LabTestResultForm(forms.ModelForm):
    """Форма для создания/редактирования результата лабораторного исследования"""
    
    class Meta:
        model = LabTestResult
        fields = ['data', 'is_completed']
        widgets = {
            'data': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class LabTestRejectionForm(forms.Form):
    """Форма для отклонения направления лабораторного исследования"""
    
    REJECTION_REASONS = [
        ('technical_issue', 'Техническая проблема'),
        ('sample_quality', 'Некачественный образец'),
        ('patient_preparation', 'Пациент не подготовлен'),
        ('equipment_failure', 'Поломка оборудования'),
        ('staff_shortage', 'Нехватка персонала'),
        ('other', 'Другая причина'),
    ]
    
    rejection_reason = forms.ChoiceField(
        choices=REJECTION_REASONS,
        label=_('Причина отклонения'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    rejection_notes = forms.CharField(
        label=_('Дополнительные комментарии'),
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )

class LabTestDisqualificationForm(forms.Form):
    """Форма для забраковки направления лабораторного исследования"""
    
    DISQUALIFICATION_REASONS = [
        ('sample_contamination', 'Загрязнение образца'),
        ('insufficient_volume', 'Недостаточный объем'),
        ('wrong_tube', 'Неправильная пробирка'),
        ('expired_sample', 'Истекший срок образца'),
        ('transport_damage', 'Повреждение при транспортировке'),
        ('labeling_error', 'Ошибка маркировки'),
        ('other', 'Другая причина'),
    ]
    
    disqualification_reason = forms.ChoiceField(
        choices=DISQUALIFICATION_REASONS,
        label=_('Причина забраковки'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    disqualification_notes = forms.CharField(
        label=_('Дополнительные комментарии'),
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )