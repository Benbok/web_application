from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import time, date
from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation
from pharmacy.widgets import MedicationSelect2Widget


class TreatmentPlanForm(forms.ModelForm):
    """
    Форма для создания/редактирования плана лечения
    """
    
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        owner_type = kwargs.pop('owner_type', None)
        owner_id = kwargs.pop('owner_id', None)
        super().__init__(*args, **kwargs)
        
        # Скрываем поля владельца, если они переданы
        if owner_type and owner_id:
            if owner_type == 'department':
                self.fields['patient_department_status'].initial = owner_id
                self.fields['encounter'].widget = forms.HiddenInput()
                self.fields['created_by'].widget = forms.HiddenInput()
            elif owner_type == 'encounter':
                self.fields['encounter'].initial = owner_id
                self.fields['patient_department_status'].widget = forms.HiddenInput()
                self.fields['created_by'].widget = forms.HiddenInput()
        
        # Делаем поля владельца необязательными для редактирования
        if self.instance.pk:
            self.fields['patient_department_status'].required = False
            self.fields['encounter'].required = False
    
    class Meta:
        model = TreatmentPlan
        fields = ['name', 'description', 'patient_department_status', 'encounter', 'created_by']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Введите название плана лечения')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Описание плана лечения (необязательно)')
            }),
            'patient_department_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'encounter': forms.Select(attrs={
                'class': 'form-select'
            }),
            'created_by': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'name': _('Название плана'),
            'description': _('Описание'),
            'patient_department_status': _('Статус пациента в отделении'),
            'encounter': _('Случай обращения'),
            'created_by': _('Создатель плана')
        }
    
    def clean(self):
        cleaned_data = super().clean()
        # Устанавливаем owner для валидации (для обратной совместимости)
        if self.owner:
            self.instance.owner = self.owner
        return cleaned_data


class TreatmentMedicationForm(forms.ModelForm):
    """
    Форма для добавления/редактирования лекарства в плане лечения
    """
    
    class Meta:
        model = TreatmentMedication
        fields = [
            'medication', 'custom_medication', 'dosage', 'frequency', 
            'route', 'duration', 'instructions'
        ]
        widgets = {
            'medication': MedicationSelect2Widget(attrs={
                'class': 'form-select',
                'data-placeholder': _('Выберите препарат из справочника')
            }),
            'custom_medication': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Введите название препарата')
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Например: 500 мг')
            }),
            'frequency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Например: 2 раза в день')
            }),
            'route': forms.Select(attrs={
                'class': 'form-select'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Например: 7 дней')
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Особые указания по применению')
            })
        }
        labels = {
            'medication': _('Препарат из справочника'),
            'custom_medication': _('Собственный препарат'),
            'dosage': _('Дозировка'),
            'frequency': _('Частота приема'),
            'route': _('Способ введения'),
            'duration': _('Длительность'),
            'instructions': _('Особые указания')
        }
        help_texts = {
            'medication': _('Выберите препарат из справочника или оставьте пустым для ввода собственного'),
            'custom_medication': _('Введите название препарата, если его нет в справочнике'),
            'dosage': _('Укажите дозировку препарата'),
            'frequency': _('Укажите частоту приема'),
            'route': _('Выберите способ введения препарата'),
            'duration': _('Укажите длительность курса лечения'),
            'instructions': _('Дополнительные указания по применению')
        }
    
    def clean(self):
        cleaned_data = super().clean()
        medication = cleaned_data.get('medication')
        custom_medication = cleaned_data.get('custom_medication')
        
        # Проверка, что указан либо препарат из справочника, либо собственный
        if not medication and not custom_medication:
            raise forms.ValidationError(
                _("Необходимо указать либо препарат из справочника, либо собственный препарат")
            )
        
        if medication and custom_medication:
            raise forms.ValidationError(
                _("Нельзя указывать одновременно препарат из справочника и собственный препарат")
            )
        
        return cleaned_data


class TreatmentMedicationWithScheduleForm(TreatmentMedicationForm):
    """
    Интегрированная форма для добавления лекарства в план лечения с настройкой расписания
    """
    
    # Поля для расписания
    start_date = forms.DateField(
        label=_('Дата начала'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        initial=date.today,
        help_text=_('С какой даты начинать прием лекарства')
    )
    
    first_time = forms.TimeField(
        label=_('Время первого приема'),
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(9, 0),
        help_text=_('Время первого приема в день')
    )
    
    times_per_day = forms.IntegerField(
        label=_('Количество приемов в день'),
        min_value=1,
        max_value=24,
        initial=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('Сколько раз в день принимать лекарство')
    )
    
    duration_days = forms.IntegerField(
        label=_('Длительность курса (дней)'),
        min_value=1,
        max_value=365,
        initial=7,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('На сколько дней планируется курс лечения')
    )
    
    # Скрытое поле для включения расписания
    enable_schedule = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput()
    )
    
    def clean(self):
        cleaned_data = super().clean()
        times_per_day = cleaned_data.get('times_per_day')
        duration_days = cleaned_data.get('duration_days')
        
        if times_per_day and duration_days:
            if times_per_day * duration_days > 1000:
                raise forms.ValidationError(
                    _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                )
        
        return cleaned_data


class QuickAddMedicationForm(TreatmentMedicationForm):
    """
    Форма для быстрого добавления рекомендованного лекарства
    """
    
    def __init__(self, *args, **kwargs):
        recommended_medication = kwargs.pop('recommended_medication', None)
        super().__init__(*args, **kwargs)
        
        if recommended_medication:
            # Если препарат рекомендован, предзаполняем поле
            if hasattr(recommended_medication, 'medication') and recommended_medication.medication:
                self.fields['medication'].initial = recommended_medication.medication.id
            elif hasattr(recommended_medication, 'name'):
                # Пытаемся найти лекарство в справочнике по имени
                from pharmacy.models import Medication
                try:
                    medication = Medication.objects.filter(name__icontains=recommended_medication.name).first()
                    if medication:
                        self.fields['medication'].initial = medication.id
                    else:
                        # Если не найдено в справочнике, заполняем как собственное
                        self.fields['custom_medication'].initial = recommended_medication.name
                except:
                    # В случае ошибки заполняем как собственное
                    self.fields['custom_medication'].initial = recommended_medication.name


class TreatmentRecommendationForm(forms.ModelForm):
    """
    Форма для создания/редактирования рекомендаций в плане лечения
    """
    
    class Meta:
        model = TreatmentRecommendation
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Введите рекомендацию...')
            })
        }
        labels = {
            'text': _('Текст рекомендации')
        }
        help_texts = {
            'text': _('Введите рекомендацию для пациента')
        } 