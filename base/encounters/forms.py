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
    class Meta:
        model = Encounter
        fields = ['date_start', 'date_end', 'doctor']
        widgets = {
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'date_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
        }
      
class EncounterCloseForm(forms.ModelForm):
    transfer_to_department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
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