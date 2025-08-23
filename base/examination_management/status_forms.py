from django import forms
from django.utils.translation import gettext_lazy as _


class RejectionForm(forms.Form):
    """Форма для отклонения назначения"""
    rejection_reason = forms.CharField(
        label=_('Причина отклонения'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Укажите причину отклонения назначения')
        }),
        required=True,
        help_text=_('Обязательно укажите причину отклонения')
    )


class PauseForm(forms.Form):
    """Форма для приостановки назначения"""
    pause_reason = forms.CharField(
        label=_('Причина приостановки'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Укажите причину приостановки назначения')
        }),
        required=False,
        help_text=_('Можно оставить пустым')
    )


class CompletionForm(forms.Form):
    """Форма для завершения назначения"""
    completion_notes = forms.CharField(
        label=_('Примечания к завершению'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Дополнительные примечания к выполнению')
        }),
        required=False,
        help_text=_('Можно оставить пустым')
    ) 