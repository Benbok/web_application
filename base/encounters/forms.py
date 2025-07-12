from django import forms
from django.contrib.auth import get_user_model
from .models import Encounter
from .services.encounter_service import EncounterService
from .strategies.outcome_strategies import OutcomeStrategyFactory
from departments.models import Department

User = get_user_model()  

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Динамически загружаем доступные исходы через Strategy Pattern
        available_outcomes = OutcomeStrategyFactory.get_available_outcomes()
        self.fields['outcome'].choices = [('', 'Выберите исход')] + [
            (code, display_name) for code, display_name in available_outcomes.items()
        ]

    def clean(self):
        cleaned_data = super().clean()
        outcome = cleaned_data.get('outcome')
        transfer_to_department = cleaned_data.get('transfer_to_department')

        if outcome == 'transferred' and not transfer_to_department:
            self.add_error('transfer_to_department', "Для перевода необходимо выбрать отделение.")
        elif outcome != 'transferred' and transfer_to_department:
            self.add_error('transfer_to_department', "Отделение для перевода может быть выбрано только при исходе 'Переведён'.")

        # Используем Strategy Pattern для валидации
        if self.instance and outcome:
            service = EncounterService(self.instance)
            outcome_processor = service.get_outcome_requirements(outcome)
            required_fields = outcome_processor.get('required_fields', [])
            
            if 'documents' in required_fields and not self.instance.documents.exists():
                raise forms.ValidationError(
                    "Невозможно закрыть случай обращения: нет прикрепленных документов."
                )

        return cleaned_data
    
    def save(self, commit=True, user=None):
        """Переопределяем save для использования Command Pattern"""
        encounter = super().save(commit=False)
        
        if commit and user:
            service = EncounterService(encounter)
            outcome = self.cleaned_data.get('outcome')
            transfer_department = self.cleaned_data.get('transfer_to_department')
            
            # Используем сервис для закрытия через команды
            success = service.close_encounter(
                outcome=outcome,
                transfer_department=transfer_department,
                user=user
            )
            
            if not success:
                raise forms.ValidationError("Не удалось закрыть случай обращения.")
        
        return encounter


class EncounterReopenForm(forms.Form):
    """Форма для возврата случая обращения в активное состояние"""
    
    confirm_reopen = forms.BooleanField(
        label="Подтверждаю возврат случая обращения в активное состояние",
        required=True,
        help_text="Это действие отменит все изменения, связанные с закрытием случая."
    )
    
    def __init__(self, encounter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encounter = encounter
    
    def clean(self):
        cleaned_data = super().clean()
        
        if not self.encounter:
            raise forms.ValidationError("Случай обращения не найден.")
        
        if self.encounter.is_active:
            raise forms.ValidationError("Случай обращения уже активен.")
        
        return cleaned_data
    
    def save(self, user=None):
        """Возвращает случай обращения в активное состояние"""
        if not self.cleaned_data.get('confirm_reopen'):
            raise forms.ValidationError("Необходимо подтвердить возврат.")
        
        service = EncounterService(self.encounter)
        success = service.reopen_encounter(user=user)
        
        if not success:
            raise forms.ValidationError("Не удалось вернуть случай обращения в активное состояние.")
        
        return self.encounter


class EncounterUndoForm(forms.Form):
    """Форма для отмены последней операции"""
    
    confirm_undo = forms.BooleanField(
        label="Подтверждаю отмену последней операции",
        required=True,
        help_text="Это действие отменит последнюю выполненную операцию."
    )
    
    def __init__(self, encounter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encounter = encounter
    
    def clean(self):
        cleaned_data = super().clean()
        
        if not self.encounter:
            raise forms.ValidationError("Случай обращения не найден.")
        
        service = EncounterService(self.encounter)
        last_command = service.get_last_command()
        
        if not last_command:
            raise forms.ValidationError("Нет операций для отмены.")
        
        if not last_command.get('can_undo'):
            raise forms.ValidationError("Последняя операция не может быть отменена.")
        
        return cleaned_data
    
    def save(self, user=None):
        """Отменяет последнюю операцию"""
        if not self.cleaned_data.get('confirm_undo'):
            raise forms.ValidationError("Необходимо подтвердить отмену.")
        
        service = EncounterService(self.encounter)
        success = service.undo_last_operation()
        
        if not success:
            raise forms.ValidationError("Не удалось отменить последнюю операцию.")
        
        return self.encounter