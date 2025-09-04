from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import time, date

from .models import ExaminationLabTest, ExaminationPlan, ExaminationInstrumental
from lab_tests.models import LabTestDefinition
from instrumental_procedures.models import InstrumentalProcedureDefinition
from clinical_scheduling.forms import ScheduleSettingsForm


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


def validate_duplicate_assignment(examination_plan, lab_test=None, instrumental_procedure=None, scheduled_time=None, start_date=None):
    """
    Проверяет, есть ли уже назначение на это же время в эту же дату
    
    Args:
        examination_plan: План обследования
        lab_test: Лабораторное исследование (для лабораторных)
        instrumental_procedure: Инструментальное исследование (для инструментальных)
        scheduled_time: Время выполнения
        start_date: Дата начала (если есть расписание)
        
    Returns:
        str: Сообщение об ошибке или None
    """
    if not scheduled_time:
        return None
    
    # Определяем дату для проверки
    check_date = start_date if start_date else examination_plan.created_at.date()
    
    # Проверяем лабораторные исследования
    if lab_test:
        existing_lab_tests = ExaminationLabTest.objects.filter(
            examination_plan=examination_plan,
            lab_test=lab_test,
            scheduled_time=scheduled_time,
            created_at__date=check_date
        )
        
        if existing_lab_tests.exists():
            return _(
                f'Лабораторное исследование "{lab_test.name}" уже назначено на {scheduled_time.strftime("%H:%M")} '
                f'в плане "{examination_plan.name}". Выберите другое время.'
            )
    
    # Проверяем инструментальные исследования
    if instrumental_procedure:
        existing_instrumentals = ExaminationInstrumental.objects.filter(
            examination_plan=examination_plan,
            instrumental_procedure=instrumental_procedure,
            scheduled_time=scheduled_time,
            created_at__date=check_date
        )
        
        if existing_instrumentals.exists():
            return _(
                f'Инструментальное исследование "{instrumental_procedure.name}" уже назначено на {scheduled_time.strftime("%H:%M")} '
                f'в плане "{examination_plan.name}". Выберите другое время.'
            )
    
    return None


def validate_future_datetime(start_date=None, scheduled_time=None):
    """
    Проверяет, что дата и время назначения не в прошлом
    
    Args:
        start_date: Дата начала назначения
        scheduled_time: Время выполнения
        
    Returns:
        str: Сообщение об ошибке или None
    """
    from django.utils import timezone
    
    now = timezone.now()
    today = now.date()
    current_time = now.time()
    
    # Проверяем дату
    if start_date and start_date < today:
        return _(
            f'Нельзя назначить исследование на прошедшую дату ({start_date.strftime("%d.%m.%Y")}). '
            f'Выберите дату не ранее сегодняшней ({today.strftime("%d.%m.%Y")}).'
        )
    
    # Проверяем время (только если дата сегодня)
    if start_date == today and scheduled_time:
        # Добавляем небольшую погрешность (1 минута) для текущего времени
        from datetime import timedelta
        current_time_with_tolerance = (timezone.now() - timedelta(minutes=1)).time()
        
        if scheduled_time < current_time_with_tolerance:
            return _(
                f'Нельзя назначить исследование на прошедшее время ({scheduled_time.strftime("%H:%M")}). '
                f'Выберите время не ранее текущего ({current_time.strftime("%H:%M")}).'
            )
    
    return None


class ExaminationLabTestForm(forms.ModelForm):
    """Форма для добавления лабораторного исследования в план обследования"""
    
    class Meta:
        model = ExaminationLabTest
        fields = ['lab_test', 'instructions', 'scheduled_time']
        widgets = {
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scheduled_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
        }


class ExaminationLabTestWithScheduleForm(ExaminationLabTestForm):
    """Интегрированная форма для добавления лабораторного исследования с настройкой расписания"""
    
    # Поля для расписания
    start_date = forms.DateField(
        label=_('Дата начала'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'placeholder': 'дд.мм.гггг'
        }),
        input_formats=['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'],
        help_text=_('С какой даты начинать расписание (формат: дд.мм.гггг)')
    )
    
    first_time = forms.TimeField(
        label=_('Время выполнения'),
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(9, 0),
        help_text=_('Время выполнения исследования')
    )
    
    times_per_day = forms.IntegerField(
        label=_('Количество раз в день'),
        min_value=1,
        max_value=24,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('Сколько раз в день выполнять исследование')
    )
    
    duration_days = forms.IntegerField(
        label=_('Длительность курса (дней)'),
        min_value=1,
        max_value=365,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        help_text=_('Лабораторные исследования обычно выполняются один раз')
    )
    
    # Скрытое поле для включения расписания
    enable_schedule = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем readonly для duration_days
        self.fields['duration_days'].widget.attrs['readonly'] = 'readonly'
    
    def clean(self):
        cleaned_data = super().clean()
        times_per_day = cleaned_data.get('times_per_day')
        duration_days = cleaned_data.get('duration_days')
        first_time = cleaned_data.get('first_time')
        start_date = cleaned_data.get('start_date')
        lab_test = cleaned_data.get('lab_test')
        
        # Проверяем количество раз в день
        if times_per_day:
            _, error = validate_and_adjust_times_per_day(times_per_day)
            if error:
                # Показываем ошибку валидации
                raise forms.ValidationError(error)
        
        if times_per_day and duration_days:
            if times_per_day * duration_days > 1000:
                raise forms.ValidationError(
                    _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                )
        
        # Проверяем дублирование назначений
        if first_time and lab_test:
            # Получаем план обследования из контекста формы
            examination_plan = getattr(self, 'examination_plan', None)
            if examination_plan:
                error = validate_duplicate_assignment(
                    examination_plan=examination_plan,
                    lab_test=lab_test,
                    scheduled_time=first_time,
                    start_date=start_date
                )
                if error:
                    raise forms.ValidationError(error)
        
        # Проверяем, что дата и время не в прошлом
        error = validate_future_datetime(start_date=start_date, scheduled_time=first_time)
        if error:
            raise forms.ValidationError(error)
        
        return cleaned_data


class ExaminationInstrumentalForm(forms.ModelForm):
    """Форма для добавления инструментального исследования в план обследования"""
    
    class Meta:
        model = ExaminationInstrumental
        fields = ['instrumental_procedure', 'instructions', 'scheduled_time']
        widgets = {
            'instrumental_procedure': forms.Select(attrs={'class': 'form-select'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scheduled_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
        }


class ExaminationInstrumentalWithScheduleForm(ExaminationInstrumentalForm):
    """Интегрированная форма для добавления инструментального исследования с настройкой расписания"""
    
    # Поля для расписания
    start_date = forms.DateField(
        label=_('Дата начала'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'placeholder': 'дд.мм.гггг'
        }),
        input_formats=['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'],
        help_text=_('С какой даты начинать расписание (формат: дд.мм.гггг)')
    )
    
    first_time = forms.TimeField(
        label=_('Время выполнения'),
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(9, 0),
        help_text=_('Время выполнения процедуры')
    )
    
    times_per_day = forms.IntegerField(
        label=_('Количество раз в день'),
        min_value=1,
        max_value=24,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('Сколько раз в день выполнять процедуру')
    )
    
    duration_days = forms.IntegerField(
        label=_('Длительность курса (дней)'),
        min_value=1,
        max_value=365,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        help_text=_('Процедуры обычно выполняются один раз')
    )
    
    # Скрытое поле для включения расписания
    enable_schedule = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем readonly для duration_days
        self.fields['duration_days'].widget.attrs['readonly'] = 'readonly'
    
    def clean(self):
        cleaned_data = super().clean()
        times_per_day = cleaned_data.get('times_per_day')
        duration_days = cleaned_data.get('duration_days')
        first_time = cleaned_data.get('first_time')
        start_date = cleaned_data.get('start_date')
        instrumental_procedure = cleaned_data.get('instrumental_procedure')
        
        # Проверяем количество раз в день
        if times_per_day:
            _, error = validate_and_adjust_times_per_day(times_per_day)
            if error:
                # Показываем ошибку валидации
                raise forms.ValidationError(error)
        
        if times_per_day and duration_days:
            if times_per_day * duration_days > 1000:
                raise forms.ValidationError(
                    _('Слишком много записей в расписании. Уменьшите количество приемов в день или длительность курса.')
                )
        
        # Проверяем дублирование назначений
        if first_time and instrumental_procedure:
            # Получаем план обследования из контекста формы
            examination_plan = getattr(self, 'examination_plan', None)
            if examination_plan:
                error = validate_duplicate_assignment(
                    examination_plan=examination_plan,
                    instrumental_procedure=instrumental_procedure,
                    scheduled_time=first_time,
                    start_date=start_date
                )
                if error:
                    raise forms.ValidationError(error)
        
        # Проверяем, что дата и время не в прошлом
        error = validate_future_datetime(start_date=start_date, scheduled_time=first_time)
        if error:
            raise forms.ValidationError(error)
        
        return cleaned_data


class ExaminationPlanForm(forms.ModelForm):
    """Форма для создания плана обследования"""
    
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        
        # Скрываем поля владельца, так как они устанавливаются в view
        if 'patient_department_status' in self.fields:
            self.fields['patient_department_status'].widget = forms.HiddenInput()
        if 'encounter' in self.fields:
            self.fields['encounter'].widget = forms.HiddenInput()
        if 'content_type' in self.fields:
            self.fields['content_type'].widget = forms.HiddenInput()
        if 'object_id' in self.fields:
            self.fields['object_id'].widget = forms.HiddenInput()
    
    class Meta:
        model = ExaminationPlan
        fields = ['name', 'description', 'priority', 'patient_department_status', 'encounter', 'content_type', 'object_id']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Введите название плана обследования')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Описание плана обследования (необязательно)')
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'patient_department_status': forms.HiddenInput(),
            'encounter': forms.HiddenInput(),
            'content_type': forms.HiddenInput(),
            'object_id': forms.HiddenInput(),
        }
        labels = {
            'name': _('Название плана'),
            'description': _('Описание'),
            'priority': _('Приоритет')
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Устанавливаем правильные поля владельца в зависимости от типа
        if self.owner:
            if hasattr(self.owner, 'patient'):  # Это PatientDepartmentStatus
                cleaned_data['patient_department_status'] = self.owner
                cleaned_data['encounter'] = None
                cleaned_data['content_type'] = None
                cleaned_data['object_id'] = None
            elif hasattr(self.owner, 'date_start'):  # Это Encounter
                cleaned_data['encounter'] = self.owner
                cleaned_data['patient_department_status'] = None
                cleaned_data['content_type'] = None
                cleaned_data['object_id'] = None
            else:  # Generic owner
                from django.contrib.contenttypes.models import ContentType
                cleaned_data['content_type'] = ContentType.objects.get_for_model(self.owner.__class__)
                cleaned_data['object_id'] = self.owner.pk
                cleaned_data['patient_department_status'] = None
                cleaned_data['encounter'] = None
        
        return cleaned_data 