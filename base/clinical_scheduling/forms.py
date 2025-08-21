from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import time, date


class ScheduleSettingsForm(forms.Form):
    """Форма для настройки параметров расписания"""
    
    start_date = forms.DateField(
        label=_('Дата начала'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        initial=date.today,
        help_text=_('С какой даты начинать расписание')
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
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('Сколько раз в день принимать/выполнять назначение')
    )
    
    duration_days = forms.IntegerField(
        label=_('Длительность курса (дней)'),
        min_value=1,
        max_value=365,
        initial=7,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_('На сколько дней планируется курс')
    )
    
    def __init__(self, *args, **kwargs):
        assignment_type = kwargs.pop('assignment_type', None)
        super().__init__(*args, **kwargs)
        
        # Настраиваем поля в зависимости от типа назначения
        if assignment_type == 'medication':
            self.fields['duration_days'].initial = 7
            self.fields['times_per_day'].initial = 2
            self.fields['times_per_day'].help_text = _('Сколько раз в день принимать лекарство')
        elif assignment_type == 'lab_test':
            self.fields['duration_days'].initial = 1
            self.fields['times_per_day'].initial = 1
            self.fields['duration_days'].widget.attrs['readonly'] = True
            self.fields['duration_days'].help_text = _('Лабораторные исследования обычно выполняются один раз')
        elif assignment_type == 'procedure':
            self.fields['duration_days'].initial = 1
            self.fields['times_per_day'].initial = 1
            self.fields['duration_days'].widget.attrs['readonly'] = True
            self.fields['duration_days'].help_text = _('Процедуры обычно выполняются один раз')
    
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