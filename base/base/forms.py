from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from .models import ArchiveConfiguration


class ArchiveForm(forms.Form):
    """
    Форма для архивирования записи
    """
    reason = forms.CharField(
        label=_("Причина архивирования"),
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Укажите причину архивирования...',
            'required': 'required'
        }),
        required=True,
        help_text=_("Объясните, почему необходимо архивировать эту запись (обязательно для заполнения)")
    )
    
    cascade = forms.BooleanField(
        label=_("Каскадное архивирование"),
        required=False,
        initial=True,
        help_text=_("Архивировать также все связанные записи")
    )
    
    confirm = forms.BooleanField(
        label=_("Подтверждаю архивирование"),
        required=True,
        help_text=_("Я понимаю, что архивирование может затронуть связанные данные")
    )
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.instance:
            # Проверяем конфигурацию архивирования
            config = ArchiveConfiguration.get_config(self.instance.__class__)
            
            # Причина всегда обязательна, но можно переопределить через конфигурацию
            if not config.require_reason:
                self.fields['reason'].required = False
                self.fields['reason'].widget.attrs.pop('required', None)
            
            # Скрываем каскадное архивирование если отключено
            if not config.cascade_archive:
                self.fields['cascade'].widget = forms.HiddenInput()
                self.fields['cascade'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.instance:
            # Проверяем, что запись не уже архивирована
            if self.instance.is_archived:
                raise ValidationError(_("Запись уже архивирована"))
            
            # Проверяем права доступа
            config = ArchiveConfiguration.get_config(self.instance.__class__)
            if config.archive_permission and self.user:
                if not self.user.has_perm(config.archive_permission):
                    raise ValidationError(_("У вас нет прав на архивирование"))
        
        return cleaned_data


class RestoreForm(forms.Form):
    """
    Форма для восстановления записи из архива
    """
    cascade = forms.BooleanField(
        label=_("Каскадное восстановление"),
        required=False,
        initial=True,
        help_text=_("Восстановить также все связанные записи")
    )
    
    confirm = forms.BooleanField(
        label=_("Подтверждаю восстановление"),
        required=True,
        help_text=_("Я понимаю, что восстановление может затронуть связанные данные")
    )
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.instance:
            # Проверяем конфигурацию восстановления
            config = ArchiveConfiguration.get_config(self.instance.__class__)
            
            # Проверяем, разрешено ли восстановление
            if not config.allow_restore:
                raise ValidationError(_("Восстановление не разрешено для данной модели"))
            
            # Скрываем каскадное восстановление если отключено
            if not config.cascade_restore:
                self.fields['cascade'].widget = forms.HiddenInput()
                self.fields['cascade'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.instance:
            # Проверяем, что запись архивирована
            if not self.instance.is_archived:
                raise ValidationError(_("Запись не архивирована"))
            
            # Проверяем права доступа
            config = ArchiveConfiguration.get_config(self.instance.__class__)
            if config.restore_permission and self.user:
                if not self.user.has_perm(config.restore_permission):
                    raise ValidationError(_("У вас нет прав на восстановление"))
        
        return cleaned_data


class BulkArchiveForm(forms.Form):
    """
    Форма для массового архивирования записей
    """
    reason = forms.CharField(
        label=_("Причина архивирования"),
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Укажите причину архивирования...',
            'required': 'required'
        }),
        required=True,
        help_text=_("Объясните, почему необходимо архивировать эти записи (обязательно для заполнения)")
    )
    
    cascade = forms.BooleanField(
        label=_("Каскадное архивирование"),
        required=False,
        initial=True,
        help_text=_("Архивировать также все связанные записи")
    )
    
    confirm = forms.BooleanField(
        label=_("Подтверждаю массовое архивирование"),
        required=True,
        help_text=_("Я понимаю, что архивирование может затронуть связанные данные")
    )
    
    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.pop('queryset', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.queryset and self.queryset.exists():
            # Проверяем конфигурацию для первой записи
            first_instance = self.queryset.first()
            if first_instance:
                config = ArchiveConfiguration.get_config(first_instance.__class__)
                
                # Причина всегда обязательна, но можно переопределить через конфигурацию
                if not config.require_reason:
                    self.fields['reason'].required = False
                    self.fields['reason'].widget.attrs.pop('required', None)
                
                # Скрываем каскадное архивирование если отключено
                if not config.cascade_archive:
                    self.fields['cascade'].widget = forms.HiddenInput()
                    self.fields['cascade'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.queryset:
            # Проверяем, что все записи не архивированы
            archived_count = self.queryset.filter(is_archived=True).count()
            if archived_count > 0:
                raise ValidationError(
                    _("Некоторые записи уже архивированы (%(count)d из %(total)d)") % {
                        'count': archived_count,
                        'total': self.queryset.count()
                    }
                )
            
            # Проверяем права доступа для первой записи
            first_instance = self.queryset.first()
            if first_instance:
                config = ArchiveConfiguration.get_config(first_instance.__class__)
                if config.archive_permission and self.user:
                    if not self.user.has_perm(config.archive_permission):
                        raise ValidationError(_("У вас нет прав на архивирование"))
        
        return cleaned_data


class ArchiveFilterForm(forms.Form):
    """
    Форма для фильтрации архивированных записей
    """
    STATUS_CHOICES = [
        ('', _('Все записи')),
        ('active', _('Активные')),
        ('archived', _('Архивированные')),
    ]
    
    status = forms.ChoiceField(
        label=_("Статус"),
        choices=STATUS_CHOICES,
        required=False,
        initial='',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    archive_reason = forms.CharField(
        label=_("Причина архивирования"),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по причине...'
        })
    )
    
    archived_by = forms.ModelChoiceField(
        label=_("Архивировано пользователем"),
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    archived_since = forms.DateField(
        label=_("Архивировано с"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    archived_until = forms.DateField(
        label=_("Архивировано до"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверяем, что дата "с" не больше даты "до"
        archived_since = cleaned_data.get('archived_since')
        archived_until = cleaned_data.get('archived_until')
        
        if archived_since and archived_until and archived_since > archived_until:
            raise ValidationError(_("Дата 'с' не может быть больше даты 'до'"))
        
        return cleaned_data
