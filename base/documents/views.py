from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from .models import ClinicalDocument, DocumentTemplate
from django.contrib.contenttypes.models import ContentType
from .forms import ClinicalDocumentForm
from encounters.models import Encounter
from django.urls import reverse



class DocumentDetailView(DetailView):
    model = ClinicalDocument
    template_name = 'documents/detail.html'
    context_object_name = 'document'


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
        # Находим сам родительский объект (конкретный Encounter или Department)
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
        context['parent_object'] = self.parent_object
        return context
    
    def get_success_url(self):
        """Редирект на страницу созданного документа."""
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
        context['parent_object'] = self.object.content_object
        return context

    def get_success_url(self):
        return reverse('documents:document_detail', kwargs={'pk': self.object.pk})



class DocumentDeleteView(DeleteView):
    model = ClinicalDocument
    template_name = 'documents/confirm_delete.html'
    context_object_name = 'document'
    
    def get_success_url(self):
        """Редирект на страницу случая, к которому принадлежал документ."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.content_object.pk})


def template_data(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    return JsonResponse({
        'title': template.name,
        'content': template.default_content,
    })