from django import forms
from django.db.models import Q
from .models import ClinicalDocument, DocumentTemplate, NeonatalDailyNote, DocumentCategory
from django.contrib.auth import get_user_model
from datetime import date, timedelta

User = get_user_model()

class ClinicalDocumentForm(forms.ModelForm):
    # Новое поле для выбора категории документа.
    # Оно заменит старое поле 'document_type'.
    # Queryset фильтруется, чтобы отображать только "конечные" категории,
    # к которым можно привязывать документы.
    document_category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.filter(is_leaf_node=True), # Показываем только конечные узлы
        required=True, # Документ обязательно должен иметь категорию
        label="Категория документа",
        empty_label="-- Выберите категорию --",
        widget=forms.Select(attrs={'class': 'form-control'}) # Добавляем класс для стилизации
    )

    # Поле для выбора шаблона остается, но его queryset будет фильтроваться
    template_choice = forms.ModelChoiceField(
        queryset=DocumentTemplate.objects.all(), # Изначальный queryset, будет фильтроваться в __init__
        required=False,
        label="Выбрать шаблон",
        empty_label="-- Не использовать шаблон --",
        widget=forms.Select(attrs={'class': 'form-control'}) # Добавляем класс для стилизации
    )

    class Meta:
        model = ClinicalDocument
        fields = ['datetime_document', 'document_category', 'template_choice']
        widgets = {
            'datetime_document': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'document_category': 'Категория документа',
            'datetime_document': 'Дата и время документа',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) # Получаем текущего пользователя
        # parent_object может быть Patient, Encounter и т.д., и может иметь атрибут 'department'
        parent_object = kwargs.pop('parent_object', None) 
        
        super().__init__(*args, **kwargs)

        # Фильтрация категорий документов по отделению, если контекст отделения доступен
        if parent_object and hasattr(parent_object, 'department') and parent_object.department:
            # Показываем категории, которые являются конечными узлами И
            # принадлежат к этому отделению ИЛИ не привязаны ни к какому отделению (глобальные)
            self.fields['document_category'].queryset = DocumentCategory.objects.filter(
                Q(is_leaf_node=True),
                Q(department=parent_object.department) | Q(department__isnull=True)
            ).order_by('name') # Добавляем сортировку
        else:
            # Если нет конкретного контекста отделения, показываем все конечные категории
            self.fields['document_category'].queryset = DocumentCategory.objects.filter(is_leaf_node=True).order_by('name')


        # Фильтрация шаблонов: глобальные или созданные текущим пользователем
        template_queryset = DocumentTemplate.objects.all().select_related('document_category')
        if user:
            template_queryset = template_queryset.filter(Q(is_global=True) | Q(author=user))
        self.fields['template_choice'].queryset = template_queryset

        # Установка начальных значений для категории и шаблона при редактировании
        if self.instance.pk: # Если редактируем существующий документ
            if self.instance.document_category:
                self.fields['document_category'].initial = self.instance.document_category
                # При редактировании фильтруем шаблоны по текущей категории документа,
                # а также по глобальным/пользовательским, чтобы обеспечить доступность текущего шаблона.
                self.fields['template_choice'].queryset = template_queryset.filter(
                    Q(document_category=self.instance.document_category) | Q(is_global=True) | Q(author=user)
                ).order_by('name')
            if self.instance.template:
                self.fields['template_choice'].initial = self.instance.template
    
    def clean(self):
        """
        Проверяет, соответствует ли выбранный шаблон выбранной категории документа.
        """
        cleaned_data = super().clean()
        document_category = cleaned_data.get('document_category')
        template_choice = cleaned_data.get('template_choice')

        if template_choice and document_category:
            # Если шаблон выбран, он должен принадлежать выбранной категории документа
            # или быть глобальным и не привязанным к какой-либо категории, что менее вероятно при новой схеме
            if template_choice.document_category != document_category:
                self.add_error(
                    'template_choice',
                    "Выбранный шаблон не соответствует выбранной категории документа."
                )

        return cleaned_data


class NeonatalDailyNoteForm(forms.ModelForm):
    class Meta:
        model = NeonatalDailyNote
        # Поле 'document' будет установлено в представлении, поэтому его исключаем здесь.
        exclude = ['document']
        widgets = {
            'age_in_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'pkv': forms.TextInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure_systolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure_mean': forms.NumberInput(attrs={'class': 'form-control'}),
            'saturation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'respiratory_therapy_type': forms.Select(attrs={'class': 'form-control'}),
            'ventilator_device': forms.TextInput(attrs={'class': 'form-control'}),
            'ventilation_mode': forms.TextInput(attrs={'class': 'form-control'}),
            'respiratory_parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'severity_assessment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            'conclusion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'management_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'observation_datetime': 'Дата и время осмотра',
            'age_in_days': 'Возраст ребенка в сутках жизни',
            'pkv': 'ПКВ (для недоношенных)',
            'temperature': 'Температура тела (°C)',
            'respiratory_rate': 'ЧД',
            'heart_rate': 'ЧСС',
            'blood_pressure_systolic': 'Систолическое АД',
            'blood_pressure_diastolic': 'Диастолическое АД',
            'blood_pressure_mean': 'Среднее АД',
            'saturation': 'Сатурация (%)',
            'respiratory_therapy_type': 'Вид респираторной терапии',
            'ventilator_device': 'Аппарат ИВЛ',
            'ventilation_mode': 'Режим вентиляции',
            'respiratory_parameters': 'Параметры респираторной терапии',
            'severity_assessment': 'Оценка тяжести состояния',
            'content': 'Текст дневника (основные наблюдения)',
            'conclusion': 'Заключение',
            'management_plan': 'План ведения',
        }
class ClinicalDocumentFilterForm(forms.Form):
    start_date = forms.DateField(
        label="От даты",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label="До даты",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    author = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('first_name', 'last_name'),
        label="Автор",
        required=False,
        empty_label="Все авторы",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search_query = forms.CharField(
        label="Поиск по тексту",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по заголовку или содержимому'})
    )