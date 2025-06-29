from django import forms
from django.db.models import Q
from .models import ClinicalDocument, DocumentTemplate

class ClinicalDocumentForm(forms.ModelForm):
    template_choice = forms.ModelChoiceField(
        queryset=DocumentTemplate.objects.none(),
        required=False,
        label="Шаблон документа",
        help_text="Выберите шаблон для автозаполнения"
    )

    class Meta:
        model = ClinicalDocument
        fields = [
            'document_type', 'template_choice', 'title', 'content'
        ]
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['template_choice'].queryset = DocumentTemplate.objects.filter(
            Q(is_global=True) | Q(author=user),
        )
