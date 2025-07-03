from django import forms
from .models import DocumentTemplate

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

def build_document_form(schema, document_type=None, user=None):
    """
    Динамически создает класс Django-формы на основе JSON-схемы.
    """
    fields = {
        # Добавляем стандартное поле для даты документа
        'datetime_document': forms.DateTimeField(
            label="Дата и время документа",
            widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
        ),
        'template_choice': forms.ModelChoiceField(
            queryset=DocumentTemplate.objects.none(), # Будет заполнен в __init__
            required=False,
            label="Выбрать шаблон",
            empty_label="-- Не использовать шаблон --",
            # widget=forms.Select(attrs={'class': 'form-control'}) # Можно добавить стили
        )
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

        # Логика для поля 'doctor'
        if field_name == 'doctor' and user:
            field_kwargs['initial'] = user.get_full_name() or user.username
            field_kwargs['widget'] = forms.TextInput(attrs={'readonly': 'readonly'})

        fields[field_name] = form_field_class(**field_kwargs)

    DynamicDocumentForm = type('DynamicDocumentForm', (forms.Form,), fields)

    # Добавляем логику для фильтрации шаблонов в __init__ формы
    original_init = DynamicDocumentForm.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if document_type:
            template_queryset = DocumentTemplate.objects.filter(document_type=document_type)
            if user and not user.is_superuser: # Если не суперпользователь, показываем только свои и глобальные
                template_queryset = template_queryset.filter(Q(is_global=True) | Q(author=user))
            self.fields['template_choice'].queryset = template_queryset

    DynamicDocumentForm.__init__ = new_init

    return DynamicDocumentForm