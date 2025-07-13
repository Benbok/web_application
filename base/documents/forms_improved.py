"""
Улучшенные формы для модуля Documents
"""
from django import forms
from django.db.models import Q
from django.core.cache import cache
from functools import lru_cache
import hashlib
import json

from .models import DocumentTemplate, DocumentType


# Расширенная карта типов полей
FIELD_TYPE_MAP = {
    'text': forms.CharField,
    'textarea': lambda **kwargs: forms.CharField(widget=forms.Textarea, **kwargs),
    'number': forms.IntegerField,
    'decimal': forms.DecimalField,
    'date': forms.DateField,
    'datetime': forms.DateTimeField,
    'checkbox': forms.BooleanField,
    'choice': forms.ChoiceField,
    'email': forms.EmailField,
    'url': forms.URLField,
    'phone': forms.CharField,  # Можно добавить валидацию телефона
    'select': forms.ChoiceField,
    'radio': forms.ChoiceField,
    'file': forms.FileField,
    'image': forms.ImageField,
}


class DocumentFormBuilder:
    """
    Класс для создания динамических форм с кэшированием
    """
    
    CACHE_PREFIX = "document_form_"
    CACHE_TIMEOUT = 3600  # 1 час
    
    @classmethod
    def get_schema_hash(cls, schema):
        """Создает хеш схемы для кэширования"""
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    @classmethod
    @lru_cache(maxsize=128)
    def build_form_class(cls, schema_hash, document_type_id, user_id):
        """
        Кэшированное создание класса формы
        """
        cache_key = f"{cls.CACHE_PREFIX}{schema_hash}_{document_type_id}_{user_id}"
        cached_form_class = cache.get(cache_key)
        
        if cached_form_class is None:
            # Получаем данные для создания формы
            document_type = DocumentType.objects.get(id=document_type_id)
            user = None
            if user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
            
            cached_form_class = cls._create_form_class(document_type.schema, document_type, user)
            cache.set(cache_key, cached_form_class, cls.CACHE_TIMEOUT)
        
        return cached_form_class
    
    @classmethod
    def _create_form_class(cls, schema, document_type=None, user=None):
        """
        Создает класс динамической формы
        """
        fields = {
            # Стандартные поля
            'datetime_document': forms.DateTimeField(
                label="Дата и время документа",
                widget=forms.DateTimeInput(
                    attrs={
                        'type': 'datetime-local',
                        'class': 'form-control',
                        'required': 'required'
                    }
                ),
                required=True
            ),
            'template_choice': forms.ModelChoiceField(
                queryset=DocumentTemplate.objects.none(),
                required=False,
                label="Выбрать шаблон",
                empty_label="-- Не использовать шаблон --",
                widget=forms.Select(attrs={'class': 'form-control'})
            ),
            'change_description': forms.CharField(
                label="Описание изменений",
                widget=forms.Textarea(attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Опишите причину изменений (опционально)'
                }),
                required=False,
                max_length=500
            )
        }
        
        # Создаем поля на основе схемы
        for field_data in schema.get('fields', []):
            field_name = field_data.get('name')
            field_type = field_data.get('type')
            field_label = field_data.get('label', field_name)
            is_required = field_data.get('required', False)
            
            if not field_name or not field_type:
                continue
            
            form_field_class = FIELD_TYPE_MAP.get(field_type)
            if not form_field_class:
                continue
            
            field_kwargs = {
                'label': field_label,
                'required': is_required,
            }
            
            # Добавляем CSS классы
            if field_type in ['text', 'textarea', 'number', 'decimal', 'email', 'url', 'phone']:
                field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
            elif field_type == 'textarea':
                field_kwargs['widget'] = forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
            elif field_type in ['select', 'choice', 'radio']:
                field_kwargs['widget'] = forms.Select(attrs={'class': 'form-control'})
            elif field_type == 'checkbox':
                field_kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'form-check-input'})
            elif field_type in ['date', 'datetime']:
                field_kwargs['widget'] = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
            elif field_type in ['file', 'image']:
                field_kwargs['widget'] = forms.FileInput(attrs={'class': 'form-control'})
            
            # Обработка специальных типов полей
            if field_type == 'choice':
                field_kwargs['choices'] = [(opt, opt) for opt in field_data.get('options', [])]
            elif field_type == 'radio':
                field_kwargs['choices'] = [(opt, opt) for opt in field_data.get('options', [])]
                field_kwargs['widget'] = forms.RadioSelect(attrs={'class': 'form-check-input'})
            elif field_type == 'select':
                field_kwargs['choices'] = [(opt, opt) for opt in field_data.get('options', [])]
            
            # Логика для поля 'doctor'
            if field_name == 'doctor' and user:
                field_kwargs['initial'] = user.get_full_name() or user.username
                field_kwargs['widget'] = forms.TextInput(attrs={
                    'readonly': 'readonly',
                    'class': 'form-control'
                })
            
            # Добавляем валидаторы
            if field_data.get('min_length'):
                field_kwargs['min_length'] = field_data['min_length']
            if field_data.get('max_length'):
                field_kwargs['max_length'] = field_data['max_length']
            if field_data.get('min_value'):
                field_kwargs['min_value'] = field_data['min_value']
            if field_data.get('max_value'):
                field_kwargs['max_value'] = field_data['max_value']
            
            fields[field_name] = form_field_class(**field_kwargs)
        
        # Создаем класс формы
        DynamicDocumentForm = type('DynamicDocumentForm', (forms.Form,), fields)
        
        # Добавляем логику для фильтрации шаблонов
        original_init = DynamicDocumentForm.__init__
        
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            if document_type:
                template_queryset = DocumentTemplate.objects.filter(
                    document_type=document_type,
                    is_active=True
                )
                if user and not user.is_superuser:
                    template_queryset = template_queryset.filter(
                        Q(is_global=True) | Q(author=user)
                    )
                self.fields['template_choice'].queryset = template_queryset
        
        DynamicDocumentForm.__init__ = new_init
        
        return DynamicDocumentForm


def build_document_form(schema, document_type=None, user=None):
    """
    Улучшенная функция для создания динамических форм с кэшированием
    """
    if document_type:
        schema_hash = DocumentFormBuilder.get_schema_hash(schema)
        user_id = user.id if user else None
        return DocumentFormBuilder.build_form_class(schema_hash, document_type.id, user_id)
    else:
        # Fallback для случаев без кэширования
        return DocumentFormBuilder._create_form_class(schema, document_type, user)


class DocumentSearchForm(forms.Form):
    """
    Форма для поиска документов
    """
    query = forms.CharField(
        label="Поисковый запрос",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите текст для поиска...'
        })
    )
    
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        label="Тип документа",
        required=False,
        empty_label="Все типы",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    author = forms.ModelChoiceField(
        queryset=None,  # Будет заполнено в __init__
        label="Автор",
        required=False,
        empty_label="Все авторы",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        label="Дата с",
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        label="Дата по",
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    is_signed = forms.ChoiceField(
        label="Статус подписи",
        choices=[
            ('', 'Все'),
            ('true', 'Подписанные'),
            ('false', 'Не подписанные')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Заполняем queryset для авторов
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['author'].queryset = User.objects.filter(
            authored_documents__isnull=False
        ).distinct()


class DocumentTemplateForm(forms.ModelForm):
    """
    Форма для создания/редактирования шаблонов
    """
    class Meta:
        model = DocumentTemplate
        fields = ['name', 'description', 'is_global', 'template_data']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'is_global': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'template_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Введите JSON данные шаблона'
            })
        }
    
    def clean_template_data(self):
        """Валидация JSON данных шаблона"""
        template_data = self.cleaned_data['template_data']
        try:
            if isinstance(template_data, str):
                json.loads(template_data)
            return template_data
        except json.JSONDecodeError:
            raise forms.ValidationError("Некорректный JSON формат")
    
    def clean(self):
        """Дополнительная валидация"""
        cleaned_data = super().clean()
        
        # Проверяем, что глобальные шаблоны может создавать только суперпользователь
        if cleaned_data.get('is_global') and not self.request.user.is_superuser:
            raise forms.ValidationError("Только администраторы могут создавать глобальные шаблоны")
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class DocumentTypeForm(forms.ModelForm):
    """
    Форма для создания/редактирования типов документов
    """
    class Meta:
        model = DocumentType
        fields = ['name', 'department', 'schema', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'schema': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Введите JSON схему документа'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def clean_schema(self):
        """Валидация JSON схемы"""
        schema = self.cleaned_data['schema']
        try:
            if isinstance(schema, str):
                schema = json.loads(schema)
            
            # Базовая валидация схемы
            if not isinstance(schema, dict):
                raise forms.ValidationError("Схема должна быть объектом")
            
            if 'fields' not in schema:
                raise forms.ValidationError("Схема должна содержать поле 'fields'")
            
            if not isinstance(schema['fields'], list):
                raise forms.ValidationError("Поле 'fields' должно быть массивом")
            
            # Валидация полей
            for i, field in enumerate(schema['fields']):
                if not isinstance(field, dict):
                    raise forms.ValidationError(f"Поле {i} должно быть объектом")
                
                if 'name' not in field:
                    raise forms.ValidationError(f"Поле {i} должно содержать 'name'")
                
                if 'type' not in field:
                    raise forms.ValidationError(f"Поле {i} должно содержать 'type'")
                
                if field['type'] not in FIELD_TYPE_MAP:
                    raise forms.ValidationError(f"Неизвестный тип поля: {field['type']}")
            
            return schema
            
        except json.JSONDecodeError:
            raise forms.ValidationError("Некорректный JSON формат") 