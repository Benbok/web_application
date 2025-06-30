from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, reverse_lazy

from .models import ClinicalDocument, DocumentTemplate
from .forms import ClinicalDocumentForm
from encounters.models import Encounter
from departments.models import Department


DEFAULT_DOCUMENT_LIST_URL = reverse_lazy('documents:document_list')


def get_dynamic_back_url(obj_or_parent_obj):
    """
    Вспомогательная функция для определения динамического URL по умолчанию для кнопки "Назад".
    
    Принимает экземпляр ClinicalDocument или родительский объект (например, Encounter или Patient).
    """
    parent_obj = None
    if isinstance(obj_or_parent_obj, ClinicalDocument):
        parent_obj = obj_or_parent_obj.content_object
    else:
        parent_obj = obj_or_parent_obj

    if parent_obj:
        content_type = ContentType.objects.get_for_model(parent_obj)
        
        if content_type.model == 'encounter':
            # Если родительский объект - Обращение, возвращаемся на его детальную страницу
            return reverse('encounters:encounter_detail', kwargs={'pk': parent_obj.pk})
        elif content_type.model == 'patientdepartmentstatus':
            return reverse('departments:department_detail', kwargs={'pk': parent_obj.pk})
        # Добавьте другие условия для других типов родительских объектов, если применимо
    return DEFAULT_DOCUMENT_LIST_URL

class DocumentDetailView(DetailView):
    model = ClinicalDocument
    template_name = 'documents/detail.html'
    context_object_name = 'document'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем 'next' из GET-параметров или пустую строку
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.object)
        return context


class DocumentCreateView(CreateView):
    model = ClinicalDocument
    form_class = ClinicalDocumentForm
    template_name = 'documents/form.html'

    def setup(self, request, *args, **kwargs):
        """Получаем объект encounter до выполнения остальной логики."""
        super().setup(request, *args, **kwargs)
        # Получаем тип контента (модель) по ее имени
        model_name = self.kwargs['model_name']
        # Например, URL может быть /add/<str:app_label>/<str:model_name>/<int:object_id>/
        content_type = get_object_or_404(ContentType, model=model_name)
        # Находим сам родительский объект
        self.parent_object = get_object_or_404(content_type.model_class(), pk=self.kwargs['object_id'])

    def get_form_kwargs(self):
        """Передаем request.user в форму для фильтрации шаблонов."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Добавляем автора и случай (encounter) перед сохранением."""
        form.instance.author = self.request.user
        form.instance.content_object = self.parent_object
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавляем в контекст шаблона заголовок и случай."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новый документ'
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.parent_object)
        context['parent_object'] = self.parent_object
        return context
    
    def get_success_url(self):
        """Редирект на страницу созданного документа."""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('documents:document_detail', kwargs={'pk': self.object.pk})



class DocumentUpdateView(UpdateView):
    model = ClinicalDocument
    form_class = ClinicalDocumentForm
    template_name = 'documents/form.html'
    context_object_name = 'document'

    def get_form_kwargs(self):
        """Точно так же передаем user в форму."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Добавляем в контекст заголовок."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактировать документ'
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.object)
        context['parent_object'] = self.object.content_object
        return context

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('documents:document_detail', kwargs={'pk': self.object.pk})



class DocumentDeleteView(DeleteView):
    model = ClinicalDocument
    template_name = 'documents/confirm_delete.html'
    context_object_name = 'document'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.object)
        return context
    
    def get_success_url(self):
        """Редирект на страницу случая, к которому принадлежал документ."""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return get_dynamic_back_url(self.object)


def template_data(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    return JsonResponse({
        'title': template.name,
        'content': template.default_content,
    })