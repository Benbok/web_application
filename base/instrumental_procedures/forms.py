from django import forms
from .models import InstrumentalProcedureResultType
from django.db.models import Q

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

def build_instrumental_procedure_result_form(schema, result_type=None, user=None, initial=None):
    """
    Динамически создает класс Django-формы на основе JSON-схемы для результатов инструментальных исследований.
    """
    fields = {
        'datetime_result': forms.DateTimeField(
            label="Дата и время результата",
            widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
        ),
    }
    
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

    DynamicInstrumentalProcedureResultForm = type('DynamicInstrumentalProcedureResultForm', (forms.Form,), fields)

    class BaseForm(DynamicInstrumentalProcedureResultForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if initial:
                for key, value in initial.items():
                    if key in self.fields:
                        self.fields[key].initial = value

    return BaseForm