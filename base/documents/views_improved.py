"""
Улучшенные представления для модуля Documents
"""
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
import json

from .models import DocumentType, ClinicalDocument, DocumentTemplate
from .services import DocumentService, DocumentTemplateService, DocumentSearchService, DocumentCacheService
from .forms import build_document_form
from departments.models import Department


class DocumentTypeSelectionView(LoginRequiredMixin, View):
    """
    Улучшенное представление для выбора типа документа
    """
    template_name = 'documents/select_document_type.html'
    
    def get(self, request, model_name, object_id):
        try:
            content_type = get_object_or_404(ContentType, model=model_name)
            parent_object = get_object_or_404(content_type.model_class(), pk=object_id)
            
            department_slug = request.GET.get('department_slug')
            if not department_slug:
                raise ValueError("Не передан параметр department_slug!")
            
            department = get_object_or_404(Department, slug=department_slug)
            
            # Получаем активные типы документов с кэшированием
            document_types = DocumentType.objects.filter(
                department=department,
                is_active=True
            ).select_related('department')
            
            # Поиск
            search_query = request.GET.get('q')
            if search_query:
                document_types = document_types.filter(
                    Q(name__icontains=search_query) | 
                    Q(schema__icontains=search_query)
                )
            
            # Пагинация
            paginator = Paginator(document_types, 20)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            context = {
                'document_types': page_obj,
                'model_name': model_name,
                'object_id': object_id,
                'next_url': request.GET.get('next', ''),
                'title': 'Выберите тип документа',
                'search_query': search_query,
                'department': department,
                'parent_object': parent_object,
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Ошибка при загрузке типов документов: {str(e)}")
            return redirect('patients:patient_list')


class DocumentCreateView(LoginRequiredMixin, View):
    """
    Улучшенное представление для создания документа
    """
    template_name = 'documents/form.html'
    
    def get(self, request, model_name, object_id, document_type_id):
        try:
            document_type = get_object_or_404(DocumentType, pk=document_type_id, is_active=True)
            content_type = get_object_or_404(ContentType, model=model_name)
            parent_object = get_object_or_404(content_type.model_class(), pk=object_id)
            
            # Получаем кэшированную форму
            DocumentForm = DocumentCacheService.get_cached_form(document_type, request.user)
            form = DocumentForm()
            
            # Получаем доступные шаблоны
            templates = DocumentCacheService.get_cached_templates(document_type, request.user)
            
            context = {
                'form': form,
                'document_type': document_type,
                'templates': templates,
                'parent_object': parent_object,
                'title': f'Создание: {document_type.name}',
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Ошибка при создании документа: {str(e)}")
            return redirect('patients:patient_list')
    
    def post(self, request, model_name, object_id, document_type_id):
        try:
            document_type = get_object_or_404(DocumentType, pk=document_type_id, is_active=True)
            content_type = get_object_or_404(ContentType, model=model_name)
            parent_object = get_object_or_404(content_type.model_class(), pk=object_id)
            
            DocumentForm = DocumentCacheService.get_cached_form(document_type, request.user)
            form = DocumentForm(request.POST)
            
            # Обработка применения шаблона
            if 'apply_template' in request.POST:
                return self._handle_template_application(request, document_type, form)
            
            if form.is_valid():
                return self._handle_form_submission(request, form, document_type, parent_object)
            
            # Повторный рендеринг формы с ошибками
            templates = DocumentCacheService.get_cached_templates(document_type, request.user)
            context = {
                'form': form,
                'document_type': document_type,
                'templates': templates,
                'parent_object': parent_object,
                'title': f'Создание: {document_type.name}',
            }
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Ошибка при создании документа: {str(e)}")
            return redirect('patients:patient_list')
    
    def _handle_template_application(self, request, document_type, form):
        """Обработка применения шаблона"""
        template_id = request.POST.get('template_choice')
        if template_id:
            template = get_object_or_404(DocumentTemplate, pk=template_id)
            
            # Применяем шаблон
            initial_data = DocumentTemplateService.apply_template(template)
            
            # Сохраняем текущее значение datetime_document
            if 'datetime_document' in request.POST and request.POST['datetime_document']:
                initial_data['datetime_document'] = request.POST['datetime_document']
            
            # Пересоздаем форму с данными шаблона
            DocumentForm = DocumentCacheService.get_cached_form(document_type, request.user)
            form = DocumentForm(initial=initial_data)
            
            templates = DocumentCacheService.get_cached_templates(document_type, request.user)
            context = {
                'form': form,
                'document_type': document_type,
                'templates': templates,
                'title': f'Создание: {document_type.name}',
            }
            return render(request, self.template_name, context)
    
    def _handle_form_submission(self, request, form, document_type, parent_object):
        """Обработка отправки формы"""
        cleaned_data = form.cleaned_data
        datetime_document = cleaned_data.pop('datetime_document')
        cleaned_data.pop('template_choice', None)  # Удаляем поле шаблона
        
        # Получаем должность автора
        author_position = None
        if hasattr(request.user, 'doctor_profile'):
            author_position = request.user.doctor_profile.get_current_position(
                at_date=datetime_document.date()
            )
        
        # Создаем документ через сервис
        document = DocumentService.create_document(
            document_type=document_type,
            content_object=parent_object,
            author=request.user,
            data=cleaned_data,
            datetime_document=datetime_document,
            author_position=author_position
        )
        
        messages.success(request, f"Документ '{document_type.name}' успешно создан")
        return redirect(request.GET.get('next', reverse('patients:patient_list')))


class DocumentDetailView(LoginRequiredMixin, View):
    """
    Улучшенное представление для отображения документа
    """
    template_name = 'documents/detail.html'
    
    def get(self, request, pk):
        try:
            document = get_object_or_404(
                ClinicalDocument.objects.with_related_data(),
                pk=pk
            )
            
            # Проверяем права доступа
            if not self._can_view_document(request.user, document):
                messages.error(request, "У вас нет прав для просмотра этого документа")
                return redirect('patients:patient_list')
            
            # Создаем форму для отображения
            DocumentForm = DocumentCacheService.get_cached_form(document.document_type, request.user)
            form = DocumentForm(initial={
                'datetime_document': document.datetime_document,
                **document.data
            })
            
            # Получаем версии документа
            versions = document.versions.order_by('-version_number')[:5]
            
            # Получаем записи аудита
            audit_logs = document.audit_logs.order_by('-timestamp')[:10]
            
            context = {
                'document': document,
                'document_type': document.document_type,
                'form': form,
                'versions': versions,
                'audit_logs': audit_logs,
                'title': f'Детали: {document.document_type.name}',
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Ошибка при загрузке документа: {str(e)}")
            return redirect('patients:patient_list')
    
    def _can_view_document(self, user, document):
        """Проверка прав на просмотр документа"""
        return user.is_superuser or document.author == user


class DocumentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Улучшенное представление для редактирования документа
    """
    template_name = 'documents/form.html'
    permission_required = 'documents.change_clinicaldocument'
    
    def dispatch(self, request, *args, **kwargs):
        self.document = get_object_or_404(ClinicalDocument, pk=kwargs['pk'])
        
        # Проверяем права на редактирование
        if not self._can_edit_document(request.user, self.document):
            messages.error(request, "У вас нет прав для редактирования этого документа")
            return redirect('documents:document_detail', pk=self.document.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, pk):
        try:
            DocumentForm = DocumentCacheService.get_cached_form(self.document.document_type, request.user)
            form = DocumentForm(initial={
                'datetime_document': self.document.datetime_document,
                **self.document.data
            })
            
            templates = DocumentCacheService.get_cached_templates(self.document.document_type, request.user)
            
            context = {
                'form': form,
                'document': self.document,
                'document_type': self.document.document_type,
                'templates': templates,
                'title': f'Редактирование: {self.document.document_type.name}',
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Ошибка при загрузке документа: {str(e)}")
            return redirect('documents:document_detail', pk=pk)
    
    def post(self, request, pk):
        try:
            DocumentForm = DocumentCacheService.get_cached_form(self.document.document_type, request.user)
            form = DocumentForm(request.POST)
            
            # Обработка применения шаблона
            if 'apply_template' in request.POST:
                return self._handle_template_application(request, form)
            
            if form.is_valid():
                return self._handle_form_submission(request, form)
            
            # Повторный рендеринг формы с ошибками
            templates = DocumentCacheService.get_cached_templates(self.document.document_type, request.user)
            context = {
                'form': form,
                'document': self.document,
                'document_type': self.document.document_type,
                'templates': templates,
                'title': f'Редактирование: {self.document.document_type.name}',
            }
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Ошибка при обновлении документа: {str(e)}")
            return redirect('documents:document_detail', pk=pk)
    
    def _can_edit_document(self, user, document):
        """Проверка прав на редактирование документа"""
        return user.is_superuser or document.author == user
    
    def _handle_template_application(self, request, form):
        """Обработка применения шаблона при редактировании"""
        template_id = request.POST.get('template_choice')
        if template_id:
            template = get_object_or_404(DocumentTemplate, pk=template_id)
            initial_data = DocumentTemplateService.apply_template(template)
            
            if 'datetime_document' in request.POST and request.POST['datetime_document']:
                initial_data['datetime_document'] = request.POST['datetime_document']
            
            DocumentForm = DocumentCacheService.get_cached_form(self.document.document_type, request.user)
            form = DocumentForm(initial=initial_data)
            
            templates = DocumentCacheService.get_cached_templates(self.document.document_type, request.user)
            context = {
                'form': form,
                'document': self.document,
                'document_type': self.document.document_type,
                'templates': templates,
                'title': f'Редактирование: {self.document.document_type.name}',
            }
            return render(request, self.template_name, context)
    
    def _handle_form_submission(self, request, form):
        """Обработка отправки формы при редактировании"""
        cleaned_data = form.cleaned_data
        datetime_document = cleaned_data.pop('datetime_document')
        cleaned_data.pop('template_choice', None)
        
        # Обновляем документ через сервис
        document = DocumentService.update_document(
            document=self.document,
            user=request.user,
            data=cleaned_data,
            datetime_document=datetime_document,
            change_description=request.POST.get('change_description', '')
        )
        
        messages.success(request, "Документ успешно обновлен")
        return redirect(request.GET.get('next', reverse('documents:document_detail', kwargs={'pk': document.pk})))


class DocumentSearchView(LoginRequiredMixin, View):
    """
    Представление для поиска документов
    """
    template_name = 'documents/search.html'
    
    def get(self, request):
        query = request.GET.get('q', '')
        filters = self._get_filters_from_request(request)
        
        if query or any(filters.values()):
            documents = DocumentSearchService.search_documents(
                query=query,
                filters=filters,
                user=request.user
            )
        else:
            documents = []
        
        # Пагинация
        paginator = Paginator(documents, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Статистика
        stats = DocumentSearchService.get_document_statistics(user=request.user)
        
        context = {
            'documents': page_obj,
            'query': query,
            'filters': filters,
            'stats': stats,
            'title': 'Поиск документов',
        }
        
        return render(request, self.template_name, context)
    
    def _get_filters_from_request(self, request):
        """Извлечение фильтров из запроса"""
        return {
            'document_type': request.GET.get('document_type'),
            'author': request.GET.get('author'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
            'is_signed': request.GET.get('is_signed'),
        }


@method_decorator(csrf_exempt, name='dispatch')
class DocumentAPIActionView(LoginRequiredMixin, View):
    """
    API для действий с документами
    """
    
    def post(self, request, pk):
        try:
            document = get_object_or_404(ClinicalDocument, pk=pk)
            action = request.POST.get('action')
            
            if not self._can_perform_action(request.user, document, action):
                return JsonResponse({'error': 'Недостаточно прав'}, status=403)
            
            if action == 'sign':
                DocumentService.sign_document(document, request.user)
                return JsonResponse({'status': 'success', 'message': 'Документ подписан'})
            
            elif action == 'cancel':
                reason = request.POST.get('reason', '')
                DocumentService.cancel_document(document, request.user, reason)
                return JsonResponse({'status': 'success', 'message': 'Документ аннулирован'})
            
            elif action == 'archive':
                DocumentService.archive_document(document, request.user)
                return JsonResponse({'status': 'success', 'message': 'Документ архивирован'})
            
            else:
                return JsonResponse({'error': 'Неизвестное действие'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def _can_perform_action(self, user, document, action):
        """Проверка прав на выполнение действия"""
        if user.is_superuser:
            return True
        
        if action in ['sign', 'cancel', 'archive']:
            return document.author == user
        
        return False 