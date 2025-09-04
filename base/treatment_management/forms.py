from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import time, date
from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation
from pharmacy.widgets import MedicationSelect2Widget


def validate_and_adjust_times_per_day(times_per_day):
    """
    Проверяет, делится ли 24 на количество раз в день без остатка.
    Если нет, возвращает ошибку валидации с рекомендацией.
    
    Args:
        times_per_day (int): Количество раз в день
        
    Returns:
        tuple: (None, ошибка_валидации_или_None)
    """
    if times_per_day is None:
        return None, None
    
    # Проверяем, делится ли 24 на количество раз в день
    if 24 % times_per_day == 0:
        return None, None
    
    # Ищем ближайшее меньшее значение, которое делится на 24
    adjusted_value = None
    for i in range(times_per_day - 1, 0, -1):
        if 24 % i == 0:
            adjusted_value = i
            break
    
    if adjusted_value:
        error = _(
            f'Количество раз в день "{times_per_day}" не позволяет равномерно распределить приемы в течение дня. '
            f'Рекомендуется использовать "{adjusted_value}" раз(а) в день '
            f'(каждые {24 // adjusted_value} часов).'
        )
        return None, error
    
    # Если не найдено подходящее значение
    error = _(
        f'Количество раз в день "{times_per_day}" не позволяет равномерно распределить приемы. '
        f'Рекомендуется использовать значения, которые делят 24 без остатка (1, 2, 3, 4, 6, 8, 12, 24).'
    )
    return None, error


class ScheduleFieldsMixin:
    """
    Миксин для добавления полей расписания к формам
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Добавляем поля расписания в self.fields
        self.fields['start_date'] = forms.DateField(
            label=_('Дата начала'),
            widget=forms.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'дд.мм.гггг'
            }),
            input_formats=['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'],
            help_text=_('С какой даты начинать (формат: дд.мм.гггг)')
        )
        
        self.fields['first_time'] = forms.TimeField(
            label=_('Время начала'),
            widget=forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
            initial=time(9, 0),
            help_text=_('Время начала в день')
        )
        
        self.fields['times_per_day'] = forms.IntegerField(
            label=_('Количество раз в день'),
            min_value=1,
            max_value=24,
            initial=2,
            widget=forms.NumberInput(attrs={'class': 'form-control'}),
            help_text=_('Сколько раз в день выполнять')
        )
        
        self.fields['duration_days'] = forms.IntegerField(
            label=_('Длительность (дней)'),
            min_value=1,
            max_value=365,
            initial=7,
            widget=forms.NumberInput(attrs={'class': 'form-control'}),
            help_text=_('На сколько дней планируется')
        )
        
        # Скрытое поле для включения расписания
        self.fields['enable_schedule'] = forms.BooleanField(
            required=False,
            initial=True,
            widget=forms.HiddenInput()
        )


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
            'medication', 'dosage', 'frequency', 
            'route', 'duration', 'instructions'
        ]
        widgets = {
            'medication': MedicationSelect2Widget(attrs={
                'class': 'form-select',
                'data-placeholder': _('Выберите препарат из справочника')
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Например: 500 мг')
            }),
            'frequency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Например: 2 раза в день')
            }),
            'route': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Например: внутрь, внутримышечно')
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
            'dosage': _('Дозировка'),
            'frequency': _('Частота приема'),
            'route': _('Способ введения'),
            'duration': _('Длительность'),
            'instructions': _('Особые указания')
        }
        help_texts = {
            'medication': _('Выберите препарат из справочника'),
            'dosage': _('Укажите дозировку препарата'),
            'frequency': _('Укажите частоту приема'),
            'route': _('Укажите способ введения препарата'),
            'duration': _('Укажите длительность курса лечения'),
            'instructions': _('Дополнительные указания по применению')
        }
    
    def clean(self):
        cleaned_data = super().clean()
        medication = cleaned_data.get('medication')
        
        # Проверка, что указан препарат из справочника
        if not medication:
            raise forms.ValidationError(
                _("Необходимо указать препарат из справочника")
            )
        
        return cleaned_data


class TreatmentMedicationWithScheduleForm(ScheduleFieldsMixin, TreatmentMedicationForm):
    """
    Интегрированная форма для добавления лекарства в план лечения с настройкой расписания
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Настраиваем поля расписания для лекарств (после super().__init__)
        if 'start_date' in self.fields:
            self.fields['start_date'].help_text = _('С какой даты начинать прием лекарства')
        if 'first_time' in self.fields:
            self.fields['first_time'].help_text = _('Время первого приема в день')
        if 'times_per_day' in self.fields:
            self.fields['times_per_day'].help_text = _('Сколько раз в день принимать лекарство')
        if 'duration_days' in self.fields:
            self.fields['duration_days'].help_text = _('На сколько дней планируется курс лечения')
        
        # Если это редактирование существующего объекта, инициализируем поля расписания
        if self.instance and self.instance.pk:
            self._initialize_schedule_fields()
    
    def _initialize_schedule_fields(self):
        """
        Инициализирует поля расписания из существующих данных
        При редактировании поля остаются пустыми для ввода врачом
        """
        try:
            from clinical_scheduling.models import ScheduledAppointment
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self.instance)
            appointments = ScheduledAppointment.objects.filter(
                content_type=content_type,
                object_id=self.instance.pk
            ).order_by('-scheduled_date', 'scheduled_time')
            
            if appointments.exists():
                # При редактировании НЕ заполняем поля автоматически
                # Врач должен ввести значения вручную
                
                # Включаем расписание, если оно существует
                if 'enable_schedule' in self.fields:
                    self.fields['enable_schedule'].initial = True
                    
        except Exception:
            # В случае ошибки оставляем поля с значениями по умолчанию
            pass
    
    def clean(self):
        cleaned_data = super().clean()
        enable_schedule = cleaned_data.get('enable_schedule')
        
        if enable_schedule:
            # Проверяем обязательные поля расписания
            start_date = cleaned_data.get('start_date')
            first_time = cleaned_data.get('first_time')
            times_per_day = cleaned_data.get('times_per_day')
            duration_days = cleaned_data.get('duration_days')
            
            if not all([start_date, first_time, times_per_day, duration_days]):
                raise forms.ValidationError(
                    _('При включении расписания все поля расписания должны быть заполнены')
                )
            
            # Проверяем количество раз в день
            if times_per_day:
                _, error = validate_and_adjust_times_per_day(times_per_day)
                if error:
                    # Показываем ошибку валидации
                    raise forms.ValidationError(error)
            
            # Проверяем разумность параметров
            if times_per_day and duration_days:
                if times_per_day * duration_days > 1000:
                    raise forms.ValidationError(
                        _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                    )
        
        return cleaned_data


class QuickAddMedicationForm(ScheduleFieldsMixin, TreatmentMedicationForm):
    """
    Форма для быстрого добавления рекомендованного лекарства с поддержкой расписания
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
        
        # Настраиваем поля расписания для быстрого добавления лекарств
        if 'start_date' in self.fields:
            self.fields['start_date'].help_text = _('С какой даты начинать прием лекарства')
        if 'first_time' in self.fields:
            self.fields['first_time'].help_text = _('Время первого приема в день')
        if 'times_per_day' in self.fields:
            self.fields['times_per_day'].help_text = _('Сколько раз в день принимать лекарство')
        if 'duration_days' in self.fields:
            self.fields['duration_days'].help_text = _('На сколько дней планируется курс лечения')
    
    def clean(self):
        cleaned_data = super().clean()
        enable_schedule = cleaned_data.get('enable_schedule')
        
        if enable_schedule:
            # Проверяем обязательные поля расписания
            start_date = cleaned_data.get('start_date')
            first_time = cleaned_data.get('first_time')
            times_per_day = cleaned_data.get('times_per_day')
            duration_days = cleaned_data.get('duration_days')
            
            if not all([start_date, first_time, times_per_day, duration_days]):
                raise forms.ValidationError(
                    _('При включении расписания все поля расписания должны быть заполнены')
                )
            
            # Проверяем количество раз в день
            if times_per_day:
                _, error = validate_and_adjust_times_per_day(times_per_day)
                if error:
                    # Показываем ошибку валидации
                    raise forms.ValidationError(error)
            
            # Проверяем разумность параметров
            if times_per_day and duration_days:
                if times_per_day * duration_days > 1000:
                    raise forms.ValidationError(
                        _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                    )
        
        return cleaned_data


class TreatmentRecommendationForm(ScheduleFieldsMixin, forms.ModelForm):
    """
    Форма для создания/редактирования рекомендаций в плане лечения с настройкой расписания
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Настраиваем поля расписания для рекомендаций (после super().__init__)
        if 'duration_days' in self.fields:
            self.fields['duration_days'].initial = 1
        if 'times_per_day' in self.fields:
            self.fields['times_per_day'].initial = 1
        if 'start_date' in self.fields:
            self.fields['start_date'].help_text = _('С какой даты начинать выполнение рекомендации')
        if 'first_time' in self.fields:
            self.fields['first_time'].help_text = _('Время начала выполнения рекомендации')
        if 'times_per_day' in self.fields:
            self.fields['times_per_day'].help_text = _('Сколько раз в день выполнять рекомендацию')
        if 'duration_days' in self.fields:
            self.fields['duration_days'].help_text = _('На сколько дней планируется выполнение рекомендации')
    
    def clean(self):
        cleaned_data = super().clean()
        enable_schedule = cleaned_data.get('enable_schedule')
        
        if enable_schedule:
            # Проверяем обязательные поля расписания
            start_date = cleaned_data.get('start_date')
            first_time = cleaned_data.get('first_time')
            times_per_day = cleaned_data.get('times_per_day')
            duration_days = cleaned_data.get('duration_days')
            
            if not all([start_date, first_time, times_per_day, duration_days]):
                raise forms.ValidationError(
                    _('При включении расписания все поля расписания должны быть заполнены')
                )
            
            # Проверяем количество раз в день
            if times_per_day:
                _, error = validate_and_adjust_times_per_day(times_per_day)
                if error:
                    # Показываем ошибку валидации
                    raise forms.ValidationError(error)
            
            # Проверяем разумность параметров
            if times_per_day and duration_days:
                if times_per_day * duration_days > 1000:
                    raise forms.ValidationError(
                        _('Слишком много записей в расписании. Уменьшите количество раз в день или длительность.')
                    )
        
        return cleaned_data 