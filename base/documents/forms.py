from django import forms
from django.db.models import Q
from .models import ClinicalDocument, DocumentTemplate
from django.contrib.auth import get_user_model
from datetime import date, timedelta

User = get_user_model()

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
            Q(is_global=True) | Q(author=user)
        )

class ClinicalDocumentFilterForm(forms.Form):
    start_date = forms.DateField(
        label="От даты",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label="До даты",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    author = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('first_name', 'last_name'),
        label="Автор",
        required=False,
        empty_label="Все авторы",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search_query = forms.CharField(
        label="Поиск по тексту",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по заголовку или содержимому'})
    )