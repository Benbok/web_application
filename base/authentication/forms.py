from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

class MedicalAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя или табельный номер',
                'autocomplete': 'username',
                'id': 'username'
            }
        ),
        label=_('Имя пользователя'),
        error_messages={
            'required': _('Введите имя пользователя'),
        }
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Пароль',
                'autocomplete': 'current-password',
                'id': 'password'
            }
        ),
        label=_('Пароль'),
        error_messages={
            'required': _('Введите пароль'),
        }
    )
    
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={'class': 'form-check-input', 'id': 'remember_me'}
        ),
        label=_('Запомнить меня')
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Проверяем, существует ли пользователь
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    raise forms.ValidationError(
                        _('Аккаунт заблокирован. Обратитесь к администратору.')
                    )
                
                # Проверяем, есть ли у пользователя профиль врача
                if not hasattr(user, 'doctor_profile'):
                    raise forms.ValidationError(
                        _('У пользователя отсутствует профиль врача. Обратитесь к администратору.')
                    )
                
            except User.DoesNotExist:
                raise forms.ValidationError(
                    _('Пользователь с таким именем не найден.')
                )
        return username
