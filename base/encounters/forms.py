from django import forms
from .models import Encounter
from departments.models import Department  

class EncounterForm(forms.ModelForm):
    class Meta:
        model = Encounter
        fields = ['date_start']
        widgets = {
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

class EncounterUpdateForm(forms.ModelForm):
    transfer_to_department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label="Переведен в отделение"
    )

    class Meta:
        model = Encounter
        fields = ['date_start', 'date_end', 'outcome', 'transfer_to_department']
        widgets = {
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'date_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'outcome': forms.Select(attrs={'class': 'form-select'}),
            'transfer_to_department': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Логика видимости поля transfer_to_department будет управляться JavaScript в шаблоне

    def clean(self):
        cleaned_data = super().clean()
        outcome = cleaned_data.get('outcome')
        transfer_to_department = cleaned_data.get('transfer_to_department')
        date_end = cleaned_data.get('date_end')

        if outcome == 'transferred' and not transfer_to_department:
            self.add_error('transfer_to_department', "Для перевода необходимо выбрать отделение.")
        elif outcome != 'transferred' and transfer_to_department:
            self.add_error('transfer_to_department', "Отделение для перевода может быть выбрано только при исходе 'Переведён'.")
        return cleaned_data
      
class EncounterCloseForm(forms.ModelForm):
    transfer_to_department = forms.ModelChoiceField(
        queryset=Department.objects.exclude(slug='admission'),
        required=False,
        label="Перевести в отделение"
    )

    class Meta:
        model = Encounter
        fields = ['outcome']
        widgets = {
            'outcome': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        outcome = cleaned_data.get('outcome')
        transfer_to_department = cleaned_data.get('transfer_to_department')

        if outcome == 'transferred' and not transfer_to_department:
            self.add_error('transfer_to_department', "Для перевода необходимо выбрать отделение.")
        elif outcome != 'transferred' and transfer_to_department:
            self.add_error('transfer_to_department', "Отделение для перевода может быть выбрано только при исходе 'Переведён'.")

        if self.instance and not self.instance.documents.exists():
            raise forms.ValidationError(
                "Невозможно закрыть случай обращения: нет прикрепленных документов."
            )
        return cleaned_data