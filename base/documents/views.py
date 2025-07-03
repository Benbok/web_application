from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from .models import DocumentType, ClinicalDocument, DocumentTemplate
from .forms import build_document_form
from decimal import Decimal

def convert_decimals_to_str(data):
    """
    Рекурсивно преобразует объекты Decimal в строки в словаре.
    """
    if isinstance(data, dict):
        return {k: convert_decimals_to_str(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_decimals_to_str(elem) for elem in data]
    elif isinstance(data, Decimal):
        return str(data)
    return data

class DocumentTypeSelectionView(View):
    """
    Представление для выбора типа документа перед его созданием.
    """
    def get(self, request, model_name, object_id):
        content_type = get_object_or_404(ContentType, model=model_name)
        parent_object = get_object_or_404(content_type.model_class(), pk=object_id)

        # Предполагаем, что parent_object является PatientDepartmentStatus
        # или имеет атрибут department
        department = None
        if hasattr(parent_object, 'department'):
            department = parent_object.department
        elif hasattr(parent_object, 'patientdepartmentstatus'): # Если это Patient, ищем связанный PatientDepartmentStatus
            # Это может быть более сложная логика, если у пациента несколько активных статусов
            # Для простоты, возьмем первый активный статус, если он есть
            from departments.models import PatientDepartmentStatus
            patient_status = PatientDepartmentStatus.objects.filter(patient=parent_object, status='accepted').first()
            if patient_status:
                department = patient_status.department

        if department:
            document_types = DocumentType.objects.filter(department=department) # Фильтруем по отделению
        else:
            document_types = DocumentType.objects.all() # Если отделение не найдено, показываем все

        search_query = request.GET.get('q')
        if search_query:
            document_types = document_types.filter(name__icontains=search_query)

        return render(request, 'documents/select_document_type.html', {
            'document_types': document_types,
            'model_name': model_name,
            'object_id': object_id,
            'next_url': request.GET.get('next', ''),
            'title': 'Выберите тип документа',
            'search_query': search_query, # Передаем поисковый запрос в шаблон
        })

class DocumentCreateView(View):
    def get(self, request, model_name, object_id, document_type_id):
        document_type = get_object_or_404(DocumentType, pk=document_type_id)
        content_type = get_object_or_404(ContentType, model=model_name)
        parent_object = get_object_or_404(content_type.model_class(), pk=object_id)

        # Создаем форму динамически на основе схемы
        DocumentForm = build_document_form(document_type.schema, document_type=document_type, user=request.user)
        form = DocumentForm()

        return render(request, 'documents/form.html', {
            'form': form,
            'document_type': document_type,
            'title': f'Создание: {document_type.name}',
        })

    def post(self, request, model_name, object_id, document_type_id):
        document_type = get_object_or_404(DocumentType, pk=document_type_id)
        content_type = get_object_or_404(ContentType, model=model_name)
        parent_object = get_object_or_404(content_type.model_class(), pk=object_id)

        DocumentForm = build_document_form(document_type.schema, document_type=document_type, user=request.user)
        form = DocumentForm(request.POST)

        if 'apply_template' in request.POST: # Обработка кнопки "Применить шаблон"
            template_id = request.POST.get('template_choice')
            if template_id:
                template_choice = get_object_or_404(DocumentTemplate, pk=template_id)
                initial_data = template_choice.template_data.copy()
                # Сохраняем текущее значение datetime_document, если оно было введено
                if 'datetime_document' in request.POST and request.POST['datetime_document']:
                    initial_data['datetime_document'] = request.POST['datetime_document']
                form = DocumentForm(initial=initial_data) # Пересоздаем форму с данными шаблона
            return render(request, 'documents/form.html', {
                'form': form,
                'document_type': document_type,
                'title': f'Создание: {document_type.name}',
            })

        if form.is_valid():
            cleaned_data = form.cleaned_data
            datetime_document = cleaned_data.pop('datetime_document')
            template_choice = cleaned_data.pop('template_choice') # Удаляем поле шаблона, оно не хранится в data

            # Преобразуем Decimal в строки перед сохранением в JSONField
            data_to_save = convert_decimals_to_str(cleaned_data)

            ClinicalDocument.objects.create(
                document_type=document_type,
                content_object=parent_object,
                author=request.user,
                datetime_document=datetime_document,
                data=data_to_save
            )
            return redirect(request.GET.get('next', reverse('patients:patient_list')))

        return render(request, 'documents/form.html', {
            'form': form,
            'document_type': document_type,
            'title': f'Создание: {document_type.name}',
        })

class DocumentDetailView(View):
    """
    Представление для отображения деталей динамического документа.
    """
    def get(self, request, pk):
        document = get_object_or_404(ClinicalDocument, pk=pk)
        document_type = document.document_type

        # Создаем форму динамически на основе схемы и заполняем ее данными документа
        DocumentForm = build_document_form(document_type.schema)
        form = DocumentForm(initial={'datetime_document': document.datetime_document, **document.data})

        return render(request, 'documents/detail.html', {
            'document': document,
            'document_type': document_type,
            'form': form, # Передаем форму для отображения полей
            'title': f'Детали: {document_type.name}',
        })

class DocumentUpdateView(View):
    """
    Представление для редактирования динамического документа.
    """
    def get(self, request, pk):
        document = get_object_or_404(ClinicalDocument, pk=pk)
        document_type = document.document_type

        DocumentForm = build_document_form(document_type.schema, document_type=document_type, user=request.user)
        form = DocumentForm(initial={'datetime_document': document.datetime_document, **document.data})

        return render(request, 'documents/form.html', {
            'form': form,
            'document': document,
            'document_type': document_type,
            'title': f'Редактирование: {document_type.name}',
        })

    def post(self, request, pk):
        document = get_object_or_404(ClinicalDocument, pk=pk)
        document_type = document.document_type

        DocumentForm = build_document_form(document_type.schema, document_type=document_type, user=request.user)
        form = DocumentForm(request.POST)

        if 'apply_template' in request.POST: # Обработка кнопки "Применить шаблон"
            template_id = request.POST.get('template_choice')
            if template_id:
                template_choice = get_object_or_404(DocumentTemplate, pk=template_id)
                initial_data = template_choice.template_data.copy()
                # Сохраняем текущее значение datetime_document, если оно было введено
                if 'datetime_document' in request.POST and request.POST['datetime_document']:
                    initial_data['datetime_document'] = request.POST['datetime_document']
                form = DocumentForm(initial=initial_data) # Пересоздаем форму с данными шаблона
            return render(request, 'documents/form.html', {
                'form': form,
                'document': document,
                'document_type': document_type,
                'title': f'Редактирование: {document_type.name}',
            })

        if form.is_valid():
            cleaned_data = form.cleaned_data
            document.datetime_document = cleaned_data.pop('datetime_document')
            template_choice = cleaned_data.pop('template_choice') # Удаляем поле шаблона
            
            # Преобразуем Decimal в строки перед сохранением в JSONField
            document.data = convert_decimals_to_str(cleaned_data)
            document.save()
            return redirect(request.GET.get('next', reverse('documents:document_detail', kwargs={'pk': document.pk})))

        return render(request, 'documents/form.html', {
            'form': form,
            'document': document,
            'document_type': document_type,
            'title': f'Редактирование: {document_type.name}',
        })

# DocumentDeleteView потребует схожих изменений.
# Мы можем реализовать ее позже.
