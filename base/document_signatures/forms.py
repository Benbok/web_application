from django import forms
from django.contrib.contenttypes.models import ContentType
from .models import DocumentSignature, SignatureWorkflow, SignatureTemplate


class SignatureForm(forms.ModelForm):
    """
    Форма для подписи документа
    """
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'placeholder': 'Комментарии к подписи (необязательно)',
            'class': 'form-control'
        }),
        required=False,
        label='Комментарии к подписи',
        help_text='Добавьте любые комментарии или замечания к подписи'
    )
    
    class Meta:
        model = DocumentSignature
        fields = ['notes']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].widget.attrs.update({
            'maxlength': 500,
            'style': 'resize: vertical;'
        })


class SignatureRejectForm(forms.ModelForm):
    """
    Форма для отклонения подписи
    """
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Укажите причину отклонения подписи...',
            'class': 'form-control'
        }),
        required=True,
        label='Причина отклонения',
        help_text='Обязательно укажите причину отклонения подписи'
    )
    
    class Meta:
        model = DocumentSignature
        fields = ['rejection_reason']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rejection_reason'].widget.attrs.update({
            'maxlength': 1000,
            'style': 'resize: vertical;'
        })


class SignatureCancelForm(forms.ModelForm):
    """
    Форма для отмены подписи
    """
    cancellation_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Укажите причину отмены подписи...',
            'class': 'form-control'
        }),
        required=True,
        label='Причина отмены',
        help_text='Обязательно укажите причину отмены подписи'
    )
    
    class Meta:
        model = DocumentSignature
        fields = ['cancellation_reason']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cancellation_reason'].widget.attrs.update({
            'maxlength': 1000,
            'style': 'resize: vertical;'
        })


class SignatureWorkflowForm(forms.ModelForm):
    """
    Форма для создания и редактирования рабочего процесса подписей
    """
    class Meta:
        model = SignatureWorkflow
        fields = [
            'name', 'workflow_type', 'description',
            'require_doctor_signature', 'require_head_signature', 
            'require_chief_signature', 'require_patient_signature',
            'auto_complete_on_doctor_signature', 'auto_complete_on_all_signatures',
            'doctor_signature_timeout_days', 'head_signature_timeout_days',
            'chief_signature_timeout_days', 'patient_signature_timeout_days',
            'allow_parallel_signatures', 'require_sequential_order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название рабочего процесса'
            }),
            'workflow_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание рабочего процесса'
            }),
            'doctor_signature_timeout_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
            'head_signature_timeout_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
            'chief_signature_timeout_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
            'patient_signature_timeout_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Добавляем CSS классы для чекбоксов
        for field_name in ['require_doctor_signature', 'require_head_signature', 
                          'require_chief_signature', 'require_patient_signature',
                          'auto_complete_on_doctor_signature', 'auto_complete_on_all_signatures',
                          'allow_parallel_signatures', 'require_sequential_order', 'is_active']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-check-input'
                })
    
    def clean(self):
        """Проверяем корректность настроек"""
        cleaned_data = super().clean()
        
        # Проверяем, что указан хотя бы один тип подписи
        require_doctor = cleaned_data.get('require_doctor_signature')
        require_head = cleaned_data.get('require_head_signature')
        require_chief = cleaned_data.get('require_chief_signature')
        require_patient = cleaned_data.get('require_patient_signature')
        
        if not any([require_doctor, require_head, require_chief, require_patient]):
            raise forms.ValidationError(
                "Должен быть указан хотя бы один тип подписи"
            )
        
        # Проверяем логику автозавершения
        auto_complete_doctor = cleaned_data.get('auto_complete_on_doctor_signature')
        auto_complete_all = cleaned_data.get('auto_complete_on_all_signatures')
        
        if auto_complete_doctor and auto_complete_all:
            raise forms.ValidationError(
                "Нельзя одновременно включить автозавершение при подписи врача и при всех подписях"
            )
        
        # Проверяем таймауты
        if require_doctor and cleaned_data.get('doctor_signature_timeout_days', 0) <= 0:
            raise forms.ValidationError(
                "Таймаут подписи врача должен быть больше 0 дней"
            )
        
        if require_head and cleaned_data.get('head_signature_timeout_days', 0) <= 0:
            raise forms.ValidationError(
                "Таймаут подписи заведующего должен быть больше 0 дней"
            )
        
        if require_chief and cleaned_data.get('chief_signature_timeout_days', 0) <= 0:
            raise forms.ValidationError(
                "Таймаут подписи главного врача должен быть больше 0 дней"
            )
        
        if require_patient and cleaned_data.get('patient_signature_timeout_days', 0) <= 0:
            raise forms.ValidationError(
                "Таймаут подписи пациента должен быть больше 0 дней"
            )
        
        return cleaned_data


class SignatureTemplateForm(forms.ModelForm):
    """
    Форма для создания и редактирования шаблонов подписей
    """
    class Meta:
        model = SignatureTemplate
        fields = [
            'name', 'description', 'workflow', 'content_types', 
            'auto_apply', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название шаблона'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание шаблона'
            }),
            'workflow': forms.Select(attrs={
                'class': 'form-control'
            }),
            'content_types': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 8
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Добавляем CSS классы для чекбоксов
        for field_name in ['auto_apply', 'is_active']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-check-input'
                })
        
        # Фильтруем content_types только активными моделями
        if 'content_types' in self.fields:
            # Получаем только модели из установленных приложений
            available_models = ContentType.objects.filter(
                app_label__in=['examination_management', 'instrumental_procedures', 
                              'lab_tests', 'treatment_management', 'prescriptions']
            ).order_by('app_label', 'model')
            
            self.fields['content_types'].queryset = available_models
            self.fields['content_types'].help_text = (
                'Выберите типы документов, к которым применяется этот шаблон'
            )


class SignatureSearchForm(forms.Form):
    """
    Форма для поиска подписей
    """
    SEARCH_CHOICES = [
        ('', 'Все типы'),
        ('doctor', 'Врач'),
        ('head_of_department', 'Заведующий отделением'),
        ('chief_physician', 'Главный врач'),
        ('patient', 'Пациент'),
        ('nurse', 'Медсестра'),
        ('technician', 'Техник'),
        ('consultant', 'Консультант'),
    ]
    
    STATUS_CHOICES = [
        ('', 'Все статусы'),
        ('pending', 'Ожидает подписи'),
        ('signed', 'Подписано'),
        ('rejected', 'Отклонено'),
        ('expired', 'Истекло'),
        ('cancelled', 'Отменено'),
    ]
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по документу...'
        }),
        label='Поиск'
    )
    
    signature_type = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Тип подписи'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Статус'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Дата с'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Дата по'
    )


class BulkSignatureForm(forms.Form):
    """
    Форма для массового создания подписей
    """
    workflow = forms.ModelChoiceField(
        queryset=SignatureWorkflow.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Рабочий процесс',
        help_text='Выберите рабочий процесс для применения к документам'
    )
    
    content_types = forms.ModelMultipleChoiceField(
        queryset=ContentType.objects.filter(
            app_label__in=['examination_management', 'instrumental_procedures', 
                          'lab_tests', 'treatment_management', 'prescriptions']
        ),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Типы документов',
        help_text='Выберите типы документов для создания подписей'
    )
    
    force_create = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Принудительное создание',
        help_text='Создать подписи даже если они уже существуют'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Сортируем content_types для удобства
        self.fields['content_types'].queryset = self.fields['content_types'].queryset.order_by(
            'app_label', 'model'
        ) 