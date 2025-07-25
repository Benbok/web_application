
from django import forms
from django.contrib.auth import get_user_model
from documents.models import DocumentType
from django.utils.text import slugify

from .models import PatientDepartmentStatus, Department

User = get_user_model()

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = '__all__'

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            slug = slugify(self.cleaned_data.get('name'))
        return slug

class PatientAcceptanceForm(forms.ModelForm):
    class Meta:
        model = PatientDepartmentStatus
        fields = ['acceptance_date']
        widgets = {
            'acceptance_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
        }
        labels = {
            'acceptance_date': 'Укажите точную дату и время принятия'
        }

class DocumentAndAssignmentFilterForm(forms.Form):
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
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.all(), # Начальный queryset, будет изменен в __init__
        label="Тип документа",
        required=False,
        empty_label="Все типы",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search_query = forms.CharField(
        label="Поиск по тексту",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по содержимому'})
    )

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        if department:
            self.fields['document_type'].queryset = DocumentType.objects.filter(department=department).order_by('name')
        else:
            # Если отделение не передано, показываем все типы документов
            self.fields['document_type'].queryset = DocumentType.objects.all().order_by('name')

