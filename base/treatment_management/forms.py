from django import forms
from django.utils.translation import gettext_lazy as _
from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation
from pharmacy.widgets import MedicationSelect2Widget


class TreatmentPlanForm(forms.ModelForm):
    """
    Форма для создания/редактирования плана лечения
    """
    
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = TreatmentPlan
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Введите название плана лечения')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Описание плана лечения (необязательно)')
            })
        }
        labels = {
            'name': _('Название плана'),
            'description': _('Описание')
        }
    
    def clean(self):
        cleaned_data = super().clean()
        # Устанавливаем owner для валидации
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