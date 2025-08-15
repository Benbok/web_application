from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Encounter, EncounterDiagnosis, TreatmentPlan, TreatmentMedication, TreatmentLabTest, ExaminationPlan, ExaminationLabTest, ExaminationInstrumental
from diagnosis.models import Diagnosis
from diagnosis.widgets import DiagnosisSelect2Widget
from pharmacy.widgets import MedicationSelect2Widget
from departments.models import Department
from encounters.services.encounter_service import EncounterService
from encounters.strategies.outcome_strategies import OutcomeStrategyFactory


User = get_user_model()

class EncounterForm(forms.ModelForm):
    class Meta:
        model = Encounter
        fields = ['date_start']
        widgets = {
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем текущую дату и время по умолчанию
        if not self.instance.pk:  # Только для новых случаев
            from django.utils import timezone
            current_time = timezone.now()
            # Форматируем для datetime-local input
            formatted_time = current_time.strftime('%Y-%m-%dT%H:%M')
            self.fields['date_start'].initial = formatted_time

class EncounterDiagnosisForm(forms.ModelForm):
    """Форма для установки диагноза в случае обращения"""
    
    diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.all(),
        required=False,
        label="Диагноз",
        empty_label="Выберите диагноз",
        widget=DiagnosisSelect2Widget(attrs={'class': 'form-select', 'id': 'diagnosis-select'})
    )
    
    class Meta:
        model = Encounter
        fields = ['diagnosis']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем текущий диагноз как начальное значение
        if self.instance and self.instance.diagnosis:
            self.fields['diagnosis'].initial = self.instance.diagnosis

class EncounterDiagnosisAdvancedForm(forms.ModelForm):
    """Форма для работы с расширенной структурой диагнозов"""
    
    encounter = forms.ModelChoiceField(
        queryset=None,  # Будет установлен в __init__
        widget=forms.HiddenInput(),
        required=True
    )
    
    diagnosis_type = forms.ChoiceField(
        choices=EncounterDiagnosis.DIAGNOSIS_TYPE_CHOICES,
        label="Тип диагноза",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.all(),
        required=False,
        label="Диагноз из справочника",
        empty_label="Выберите диагноз из справочника",
        widget=DiagnosisSelect2Widget(attrs={'class': 'form-select', 'id': 'diagnosis-select'})
    )
    
    custom_diagnosis = forms.CharField(
        max_length=500,
        required=False,
        label="Собственный диагноз",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text="Введите диагноз в свободной форме"
    )
    
    description = forms.CharField(
        max_length=1000,
        required=False,
        label="Описание",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text="Дополнительное описание диагноза"
    )
    
    class Meta:
        model = EncounterDiagnosis
        fields = ['encounter', 'diagnosis_type', 'diagnosis', 'custom_diagnosis', 'description']
    
    def __init__(self, *args, **kwargs):
        encounter = kwargs.pop('encounter', None)
        super().__init__(*args, **kwargs)
        
        if encounter:
            self.fields['encounter'].queryset = Encounter.objects.filter(pk=encounter.pk)
            self.fields['encounter'].initial = encounter
    
    def clean(self):
        cleaned_data = super().clean()
        diagnosis = cleaned_data.get('diagnosis')
        custom_diagnosis = cleaned_data.get('custom_diagnosis')
        

        
        if not diagnosis and not custom_diagnosis:
            raise ValidationError("Необходимо выбрать диагноз из справочника или ввести собственный диагноз")
        
        if diagnosis and custom_diagnosis:
            raise ValidationError("Нельзя одновременно выбирать диагноз из справочника и вводить собственный")
        
        return cleaned_data

class TreatmentPlanForm(forms.ModelForm):
    """Форма для создания/редактирования плана лечения"""
    
    class Meta:
        model = TreatmentPlan
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class TreatmentMedicationForm(forms.ModelForm):
    """Форма для добавления лекарства в план лечения"""
    
    medication = forms.ModelChoiceField(
        queryset=None,  # Будет установлен в __init__
        required=False,
        label="Препарат из справочника",
        empty_label="Выберите препарат из справочника",
        widget=MedicationSelect2Widget(attrs={'class': 'form-select', 'id': 'medication-select'})
    )
    
    custom_medication = forms.CharField(
        max_length=200,
        required=False,
        label="Собственный препарат",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Введите название препарата в свободной форме"
    )
    
    dosage = forms.CharField(
        max_length=100,
        label="Дозировка",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Например: '500 мг', '1 таблетка'"
    )
    
    frequency = forms.CharField(
        max_length=100,
        label="Частота приема",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Например: '2 раза в день', 'каждые 8 часов'"
    )
    
    route = forms.ChoiceField(
        choices=TreatmentMedication.ROUTE_CHOICES,
        label="Способ применения",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    duration = forms.CharField(
        max_length=100,
        required=False,
        label="Длительность курса",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Например: '7 дней', 'до улучшения'"
    )
    
    instructions = forms.CharField(
        max_length=500,
        required=False,
        label="Особые указания",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text="Дополнительные инструкции по применению"
    )
    
    class Meta:
        model = TreatmentMedication
        fields = ['medication', 'custom_medication', 'dosage', 'frequency', 'route', 'duration', 'instructions']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Импортируем модель Medication здесь, чтобы избежать циклических импортов
        from pharmacy.models import Medication
        self.fields['medication'].queryset = Medication.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        medication = cleaned_data.get('medication')
        custom_medication = cleaned_data.get('custom_medication')
        
        if not medication and not custom_medication:
            raise ValidationError("Необходимо выбрать препарат из справочника или ввести собственный препарат")
        
        if medication and custom_medication:
            raise ValidationError("Нельзя одновременно выбирать препарат из справочника и вводить собственный")
        
        return cleaned_data

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


class TreatmentLabTestForm(forms.ModelForm):
    """Форма для добавления лабораторного исследования в план лечения"""
    
    class Meta:
        model = TreatmentLabTest
        fields = [
            'lab_test', 'custom_lab_test', 'priority', 'instructions', 'is_active'
        ]
        widgets = {
            'lab_test': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Выберите исследование из справочника'
            }),
            'custom_lab_test': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Или введите название исследования вручную'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительные инструкции по проведению исследования'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'lab_test': 'Исследование из справочника',
            'custom_lab_test': 'Собственное исследование',
            'priority': 'Приоритет',
            'instructions': 'Особые указания',
            'is_active': 'Активно',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Загружаем доступные лабораторные исследования
        from lab_tests.models import LabTestDefinition
        self.fields['lab_test'].queryset = LabTestDefinition.objects.all().order_by('name')
        self.fields['lab_test'].empty_label = "Выберите исследование из справочника"
    
    def clean(self):
        cleaned_data = super().clean()
        lab_test = cleaned_data.get('lab_test')
        custom_lab_test = cleaned_data.get('custom_lab_test')
        
        if not lab_test and not custom_lab_test:
            raise ValidationError("Необходимо выбрать исследование из справочника или ввести собственное")
        
        if lab_test and custom_lab_test:
            raise ValidationError("Нельзя одновременно выбирать исследование из справочника и вводить собственное")
        
        return cleaned_data


class ExaminationPlanForm(forms.ModelForm):
    """Форма для создания/редактирования плана обследования"""
    
    class Meta:
        model = ExaminationPlan
        fields = ['name', 'description', 'priority', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Название плана обследования',
            'description': 'Описание',
            'priority': 'Приоритет',
            'is_active': 'Активен',
        }


class ExaminationLabTestForm(forms.ModelForm):
    """Форма для добавления лабораторного исследования в план обследования"""
    
    lab_test_definition = forms.ModelChoiceField(
        queryset=None,
        label="Лабораторное исследование",
        empty_label="Выберите исследование из справочника",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ExaminationLabTest
        fields = [
            'instructions', 'is_active'
        ]
        widgets = {
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительные инструкции по проведению исследования'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'instructions': 'Особые указания',
            'is_active': 'Активно',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Загружаем доступные лабораторные исследования
        from lab_tests.models import LabTestDefinition
        self.fields['lab_test_definition'].queryset = LabTestDefinition.objects.all().order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        lab_test_definition = cleaned_data.get('lab_test_definition')
        
        if not lab_test_definition:
            raise ValidationError("Необходимо выбрать лабораторное исследование из справочника")
        
        return cleaned_data


class ExaminationInstrumentalForm(forms.ModelForm):
    """Форма для добавления инструментального исследования в план обследования"""
    
    class Meta:
        model = ExaminationInstrumental
        fields = [
            'instrumental_procedure', 'custom_procedure', 'instructions', 'is_active'
        ]
        widgets = {
            'instrumental_procedure': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Выберите исследование из справочника'
            }),
            'custom_procedure': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Или введите название исследования вручную'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительные инструкции по проведению исследования'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'instrumental_procedure': 'Исследование из справочника',
            'custom_procedure': 'Собственное исследование',
            'instructions': 'Особые указания',
            'is_active': 'Активно',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Загружаем доступные инструментальные исследования
        try:
            from instrumental_procedures.models import InstrumentalProcedureDefinition
            self.fields['instrumental_procedure'].queryset = InstrumentalProcedureDefinition.objects.all().order_by('name')
            self.fields['instrumental_procedure'].empty_label = "Выберите исследование из справочника"
        except ImportError:
            # Если приложение instrumental_procedures не установлено
            self.fields['instrumental_procedure'].queryset = []
            self.fields['instrumental_procedure'].help_text = "Приложение инструментальных исследований не установлено"
    
    def clean(self):
        cleaned_data = super().clean()
        instrumental_procedure = cleaned_data.get('instrumental_procedure')
        custom_procedure = cleaned_data.get('custom_procedure')
        
        if not instrumental_procedure and not custom_procedure:
            raise ValidationError("Необходимо выбрать исследование из справочника или ввести собственное")
        
        if instrumental_procedure and custom_procedure:
            raise ValidationError("Нельзя одновременно выбирать исследование из справочника и вводить собственное")
        
        return cleaned_data