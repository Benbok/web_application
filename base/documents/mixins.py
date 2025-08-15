from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .models import DocumentTemplate


class TemplateApplicationMixin:
    """
    Миксин для обработки применения шаблона к документу.
    Устраняет дублирование кода между DocumentCreateView и DocumentUpdateView.
    """
    
    def handle_template_application(self, request, form, document_type, document=None):
        """
        Обрабатывает применение шаблона к документу.
        
        Args:
            request: HTTP запрос
            form: Форма документа
            document_type: Тип документа
            document: Существующий документ (для редактирования) или None (для создания)
            
        Returns:
            tuple: (form, context_data) для рендеринга
        """
        template_id = request.POST.get('template_choice')
        if not template_id:
            return form, self._get_form_context(document_type, document)
        
        try:
            template_choice = get_object_or_404(DocumentTemplate, pk=template_id)
            initial_data = template_choice.template_data.copy()
            
            # Сохраняем текущее значение datetime_document, если оно было введено
            if 'datetime_document' in request.POST and request.POST['datetime_document']:
                initial_data['datetime_document'] = request.POST['datetime_document']
            
            # Пересоздаем форму с данными шаблона
            form = form.__class__(initial=initial_data)
            
            # Добавляем сообщение об успешном применении шаблона
            messages.success(request, f"Шаблон '{template_choice.name}' успешно применен")
            
        except Exception as e:
            messages.error(request, f"Ошибка при применении шаблона: {str(e)}")
        
        return form, self._get_form_context(document_type, document)
    
    def _get_form_context(self, document_type, document=None):
        """
        Формирует контекст для рендеринга формы.
        
        Args:
            document_type: Тип документа
            document: Существующий документ или None
            
        Returns:
            dict: Контекст для рендеринга
        """
        context = {
            'document_type': document_type,
        }
        
        if document:
            context.update({
                'document': document,
                'title': f'Редактирование: {document_type.name}',
            })
        else:
            context['title'] = f'Создание: {document_type.name}'
        
        return context


class DocumentPermissionMixin:
    """
    Миксин для проверки прав доступа к документу.
    Устраняет дублирование логики проверки прав в различных views.
    """
    
    def check_document_permissions(self, request, document, action='access'):
        """
        Проверяет права пользователя на выполнение действия с документом.
        
        Args:
            request: HTTP запрос
            document: Документ для проверки
            action: Действие ('access', 'edit', 'delete')
            
        Returns:
            bool: True если есть права, False если нет
        """
        # Суперпользователи могут все
        if request.user.is_superuser:
            return True
        
        # Проверяем права в зависимости от действия
        if action == 'access':
            # Для просмотра: автор или персонал
            return (document.author == request.user or 
                   request.user.is_staff)
        
        elif action == 'edit':
            # Для редактирования: только автор
            if document.author != request.user:
                messages.error(request, "У вас нет прав для редактирования этого документа.")
                return False
            return True
        
        elif action == 'delete':
            # Для удаления: только автор
            if document.author != request.user:
                messages.error(request, "У вас нет прав для удаления этого документа.")
                return False
            return True
        
        return False
    
    def get_document_or_404(self, pk):
        """
        Получает документ или возвращает 404.
        
        Args:
            pk: ID документа
            
        Returns:
            ClinicalDocument: Документ
        """
        from .models import ClinicalDocument
        return get_object_or_404(ClinicalDocument, pk=pk) 