from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from .models import DocumentType, ClinicalDocument, DocumentTemplate
from decimal import Decimal

from .forms import build_document_form
from departments.models import Department

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

        department_slug = request.GET.get('department_slug')
        if not department_slug:
            raise ValueError("Не передан параметр department_slug!")

        department = get_object_or_404(Department, slug=department_slug)
        document_types = DocumentType.objects.filter(department=department)

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

            # Получаем текущую должность автора
            author_position = None
            if request.user.is_authenticated and hasattr(request.user, 'doctor_profile'):
                author_position = request.user.doctor_profile.get_current_position(at_date=datetime_document.date())

            ClinicalDocument.objects.create(
                document_type=document_type,
                content_object=parent_object,
                author=request.user,
                author_position=author_position, # Сохраняем должность автора
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

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

# ... (остальной код)

class DocumentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Представление для редактирования динамического документа.
    """
    permission_required = 'documents.change_clinicaldocument' # Требуемое разрешение

    def dispatch(self, request, *args, **kwargs):
        self.document = get_object_or_404(ClinicalDocument, pk=kwargs['pk'])
        
        # Суперпользователи могут редактировать любой документ
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        # Только автор может редактировать документ
        if self.document.author != request.user:
            messages.error(request, "У вас нет прав для редактирования этого документа.")
            return redirect(reverse('documents:document_detail', kwargs={'pk': self.document.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        document = self.document
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
        document = self.document
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
            
            # Получаем текущую должность автора на момент документа
            if request.user.is_authenticated and hasattr(request.user, 'doctor_profile'):
                document.author_position = request.user.doctor_profile.get_current_position(at_date=document.datetime_document.date())

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

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages

# ... (остальной код)

class DocumentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Представление для удаления динамического документа.
    """
    permission_required = 'documents.delete_clinicaldocument' # Требуемое разрешение

    def dispatch(self, request, *args, **kwargs):
        self.document = get_object_or_404(ClinicalDocument, pk=kwargs['pk'])
        
        # Суперпользователи могут удалять любой документ
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        # Только автор может удалять документ
        if self.document.author != request.user:
            messages.error(request, "У вас нет прав для удаления этого документа.")
            return redirect(reverse('documents:document_detail', kwargs={'pk': self.document.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        # Обычно для удаления используется POST-запрос, но для простоты можно сделать и через GET
        # В реальном приложении лучше использовать форму с POST-запросом для удаления
        document = self.document
        return render(request, 'documents/confirm_delete.html', {'document': document, 'title': 'Удалить документ'})

    def post(self, request, pk):
        document = self.document
        document.delete()
        messages.success(request, "Документ успешно удален.")
        return redirect(request.GET.get('next', reverse('patients:patient_list')))

# ============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ ПЕЧАТИ ДОКУМЕНТОВ
# ============================================================================

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .services import DocumentPrintService, DocumentTemplateService

@method_decorator(login_required, name='dispatch')
class DocumentPrintView(View):
    """
    Представление для печати документа в PDF формате
    """
    
    def get(self, request, document_id):
        try:
            # Получаем документ
            clinical_document = get_object_or_404(ClinicalDocument, pk=document_id)
            
            # Проверяем права доступа (можно добавить дополнительную логику)
            if not request.user.is_staff and clinical_document.author != request.user:
                return HttpResponse("Доступ запрещен", status=403)
            
            # Генерируем PDF
            print_service = DocumentPrintService()
            pdf_bytes = print_service.generate_pdf(clinical_document)
            
            # Формируем имя файла
            filename = f"{clinical_document.document_type.name}_{clinical_document.datetime_document.strftime('%Y%m%d')}.pdf"
            filename = filename.replace(' ', '_').replace('/', '_')
            
            # Возвращаем PDF как ответ
            response = HttpResponse(pdf_bytes.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            print(f"Ошибка при печати документа: {e}")
            return HttpResponse(f"Ошибка при генерации PDF: {str(e)}", status=500)


@method_decorator(login_required, name='dispatch')
class DocumentPrintPreviewView(View):
    """
    Представление для предварительного просмотра документа перед печатью
    """
    
    def get(self, request, document_id):
        try:
            # Получаем документ
            clinical_document = get_object_or_404(ClinicalDocument, pk=document_id)
            
            # Проверяем права доступа
            if not request.user.is_staff and clinical_document.author != request.user:
                return HttpResponse("Доступ запрещен", status=403)
            
            # Получаем шаблон для печати
            template_service = DocumentTemplateService()
            template_name = template_service.get_print_template(clinical_document.document_type)
            
            # Формируем контекст
            context = {
                'document': clinical_document,
                'document_type': clinical_document.document_type,
                'data': clinical_document.data,
                'author': clinical_document.author,
                'datetime_document': clinical_document.datetime_document,
                'is_signed': clinical_document.is_signed,
                'signature_date': clinical_document.updated_at if clinical_document.is_signed else None,
            }
            
            return render(request, template_name, context)
            
        except Exception as e:
            print(f"Ошибка при предварительном просмотре: {e}")
            return HttpResponse(f"Ошибка при загрузке документа: {str(e)}", status=500)


@method_decorator(login_required, name='dispatch')
class DocumentPrintListView(View):
    """
    Представление для списка документов с возможностью печати
    """
    
    def get(self, request):
        try:
            # Получаем документы пользователя (или все, если staff)
            if request.user.is_staff:
                documents = ClinicalDocument.objects.all().select_related(
                    'document_type', 'author', 'content_type'
                ).order_by('-datetime_document')
            else:
                documents = ClinicalDocument.objects.filter(
                    author=request.user
                ).select_related(
                    'document_type', 'author', 'content_type'
                ).order_by('-datetime_document')
            
            # Фильтрация по типу документа
            document_type_filter = request.GET.get('document_type')
            if document_type_filter:
                documents = documents.filter(document_type_id=document_type_filter)
            
            # Поиск по названию
            search_query = request.GET.get('q')
            if search_query:
                documents = documents.filter(
                    document_type__name__icontains=search_query
                )
            
            # Получаем доступные типы документов для фильтра
            document_types = DocumentType.objects.all().order_by('name')
            
            context = {
                'documents': documents,
                'document_types': document_types,
                'search_query': search_query,
                'selected_document_type': document_type_filter,
                'title': 'Документы для печати'
            }
            
            return render(request, 'documents/print_list.html', context)
            
        except Exception as e:
            print(f"Ошибка при загрузке списка документов: {e}")
            return HttpResponse(f"Ошибка при загрузке списка: {str(e)}", status=500)


@method_decorator(login_required, name='dispatch')
class DocumentPrintSettingsView(View):
    """
    Представление для настройки параметров печати
    """
    
    def get(self, request, document_id):
        try:
            clinical_document = get_object_or_404(ClinicalDocument, pk=document_id)
            
            # Проверяем права доступа
            if not request.user.is_staff and clinical_document.author != request.user:
                return HttpResponse("Доступ запрещен", status=403)
            
            # Получаем доступные шрифты
            from .services import DocumentPrintService
            available_fonts = DocumentPrintService.get_available_fonts()
            
            context = {
                'document': clinical_document,
                'document_type': clinical_document.document_type,
                'available_fonts': available_fonts,
                'title': f'Настройки печати: {clinical_document.document_type.name}'
            }
            
            return render(request, 'documents/print_settings.html', context)
            
        except Exception as e:
            print(f"Ошибка при загрузке настроек печати: {e}")
            return HttpResponse(f"Ошибка при загрузке настроек: {str(e)}", status=500)
    
    def post(self, request, document_id):
        try:
            clinical_document = get_object_or_404(ClinicalDocument, pk=document_id)
            
            # Проверяем права доступа
            if not request.user.is_staff and clinical_document.author != request.user:
                return HttpResponse("Доступ запрещен", status=403)
            
            # Получаем параметры печати
            print_settings = {
                'font_size': int(request.POST.get('font_size', 12)),
                'font_name': request.POST.get('font_name', 'DejaVuSans'),
                'include_header': request.POST.get('include_header') == 'on',
                'include_footer': request.POST.get('include_footer') == 'on',
                'page_orientation': request.POST.get('page_orientation', 'portrait'),
                'page_size': request.POST.get('page_size', 'A4'),
                'margins': request.POST.get('margins', 'normal')
            }
            
            # Генерируем PDF с настройками
            print_service = DocumentPrintService()
            
            # Применяем настройки к сервису
            if print_settings['font_size'] != 12:
                print_service.font_size = print_settings['font_size']
                print_service.line_height = print_settings['font_size'] + 4
            
            # Применяем выбранный шрифт
            if print_settings['font_name']:
                print_service.set_font(print_settings['font_name'])
            
            # Генерируем PDF с настройками
            pdf_bytes = print_service.generate_pdf(clinical_document, print_settings=print_settings)
            
            # Формируем имя файла
            filename = f"{clinical_document.document_type.name}_{clinical_document.datetime_document.strftime('%Y%m%d')}_custom.pdf"
            filename = filename.replace(' ', '_').replace('/', '_')
            
            # Возвращаем PDF как ответ
            response = HttpResponse(pdf_bytes.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            print(f"Ошибка при печати с настройками: {e}")
            return HttpResponse(f"Ошибка при генерации PDF: {str(e)}", status=500)
