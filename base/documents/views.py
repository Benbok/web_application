# views.py
# views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, reverse_lazy
from django.db import transaction

from .models import ClinicalDocument, DocumentTemplate, NeonatalDailyNote, DocumentCategory
from .forms import ClinicalDocumentForm, NeonatalDailyNoteForm

DEFAULT_DOCUMENT_LIST_URL = reverse_lazy('documents:document_list')


class NeonatalNoteMixin:
    """Миксин для обработки неонатальных дневников"""

    @property
    def is_neonatology_department(self):
        """Проверяет, относится ли документ к отделению неонатологии"""
        department = getattr(self.parent_object, 'department', None)
        return department and department.name.lower() == 'неонатология'

    def get_daily_note_category_id(self):
        """Возвращает ID категории 'Ежедневные дневники'"""
        try:
            return DocumentCategory.objects.get(name="Ежедневные дневники", is_leaf_node=True).id
        except DocumentCategory.DoesNotExist:
            return None

    def is_daily_note_category(self, category_id):
        """Проверяет, является ли категория дневником"""
        daily_note_id = self.get_daily_note_category_id()
        return daily_note_id and int(category_id) == daily_note_id

    def get_neonatal_note_form(self, instance=None, data=None):
        """Возвращает форму для неонатального дневника"""
        return NeonatalDailyNoteForm(instance=instance, data=data)

    def get_neonatal_note_instance(self):
        """Возвращает экземпляр неонатального дневника"""
        try:
            return self.object.neonatal_daily_note
        except NeonatalDailyNote.DoesNotExist:
            return None


class BaseDocumentView:
    """Базовый класс для работы с документами"""

    def get_dynamic_back_url(self, obj_or_parent_obj):
        """Определяет URL для кнопки 'Назад'"""
        parent_obj = obj_or_parent_obj.content_object if isinstance(obj_or_parent_obj,
                                                                    ClinicalDocument) else obj_or_parent_obj

        if not parent_obj:
            return DEFAULT_DOCUMENT_LIST_URL

        content_type = ContentType.objects.get_for_model(parent_obj)
        url_mapping = {
            'encounter': reverse('encounters:encounter_detail', kwargs={'pk': parent_obj.pk}),
            'patientdepartmentstatus': reverse('departments:department_detail', kwargs={'pk': parent_obj.pk}),
            'treatmentassignment': reverse('treatment_assignments:assignment_detail', kwargs={'pk': parent_obj.pk}),
        }

        return url_mapping.get(content_type.model, DEFAULT_DOCUMENT_LIST_URL)

    def get_context_data(self, **kwargs):
        """Базовый контекст для всех представлений"""
        context = super().get_context_data(**kwargs)
        context.update({
            'next_url': self.request.GET.get('next', ''),
            'default_back_url': self.get_dynamic_back_url(
                self.object if hasattr(self, 'object') else self.parent_object),
            'daily_note_category_id': self.get_daily_note_category_id() if hasattr(self,
                                                                                   'get_daily_note_category_id') else None,
        })
        return context

    def get_selected_category(self, form):
        """Получает выбранную категорию из формы (общий метод для Create/Update)"""
        if form.is_bound:
            try:
                return int(form.data.get('document_category', 0))
            except (TypeError, ValueError):
                return None
        return getattr(self.object, 'document_category_id', None) if hasattr(self, 'object') else None

class DocumentCreateView(NeonatalNoteMixin, BaseDocumentView, CreateView):
    model = ClinicalDocument
    form_class = ClinicalDocumentForm
    template_name = 'documents/form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        model_name = self.kwargs['model_name']
        content_type = get_object_or_404(ContentType, model=model_name)
        self.parent_object = get_object_or_404(content_type.model_class(), pk=self.kwargs['object_id'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user, 'parent_object': self.parent_object})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новый документ'
        context['parent_object'] = self.parent_object

        form = kwargs.get('form', context.get('form', self.get_form()))
        selected_category = self.get_selected_category(form)

        show_neonatal = (selected_category and
                         self.is_neonatology_department and
                         self.is_daily_note_category(selected_category))

        context['show_neonatal_note_form'] = show_neonatal
        context['neonatal_note_form'] = (self.get_neonatal_note_form(data=self.request.POST)
                                         if show_neonatal and 'neonatal_note_form' not in kwargs
                                         else kwargs.get('neonatal_note_form'))

        return context

    def get_selected_category(self, form):
        """Получает выбранную категорию из формы"""
        if form.is_bound:
            try:
                return int(form.data.get('document_category', 0))
            except (TypeError, ValueError):
                return None
        return None

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        selected_category = self.get_selected_category(form)

        if 'show_extra' in request.POST:
            neonatal_note_form = (self.get_neonatal_note_form()
                                  if selected_category and self.is_neonatology_department and self.is_daily_note_category(
                selected_category)
                                  else None)
            return self.render_to_response(self.get_context_data(form=form, neonatal_note_form=neonatal_note_form))

        if form.is_valid():
            if selected_category and self.is_neonatology_department and self.is_daily_note_category(selected_category):
                neonatal_note_form = self.get_neonatal_note_form(data=request.POST)
                if neonatal_note_form.is_valid():
                    return self.forms_valid(form, neonatal_note_form)
                return self.forms_invalid(form, neonatal_note_form)
            return self.form_valid(form)

        return self.form_invalid(form)

    def forms_valid(self, clinical_form, neonatal_note_form):
        with transaction.atomic():
            clinical_document = clinical_form.save(commit=False)
            clinical_document.author = self.request.user
            clinical_document.content_object = self.parent_object
            clinical_document.save()
            self.object = clinical_document

            neonatal_note = neonatal_note_form.save(commit=False)
            neonatal_note.document = clinical_document
            neonatal_note.save()

        return redirect(self.get_success_url())

    def forms_invalid(self, clinical_form, neonatal_note_form):
        return self.render_to_response(
            self.get_context_data(form=clinical_form, neonatal_note_form=neonatal_note_form)
        )

    def get_success_url(self):
        return self.request.GET.get('next') or reverse('documents:document_detail', kwargs={'pk': self.object.pk})


class DocumentUpdateView(NeonatalNoteMixin, BaseDocumentView, UpdateView):
    model = ClinicalDocument
    form_class = ClinicalDocumentForm
    template_name = 'documents/form.html'
    context_object_name = 'document'

    @property
    def parent_object(self):
        """Возвращает родительский объект для UpdateView"""
        return self.object.content_object

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'parent_object': self.parent_object
        })
        return kwargs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'parent_object': self.object.content_object
        })
        return kwargs


    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        selected_category = self.get_selected_category(form)

        if 'show_extra' in request.POST:
            # При нажатии "Продолжить" показываем обе формы
            selected_category = self.get_selected_category(form)
            neonatal_note_form = None

            if selected_category and self.is_neonatology_department and self.is_daily_note_category(selected_category):
                neonatal_note_form = self.get_neonatal_note_form(instance=self.get_neonatal_note_instance())

            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    neonatal_note_form=neonatal_note_form,
                    show_neonatal_note_form=bool(neonatal_note_form)
                )
            )

        if form.is_valid():
            new_category = form.cleaned_data['document_category']
            was_daily_note = self.object.document_category and self.is_daily_note_category(
                self.object.document_category.id)
            is_daily_note_now = new_category and self.is_daily_note_category(new_category.id)

            if is_daily_note_now:
                neonatal_note_form = self.get_neonatal_note_form(
                    instance=self.get_neonatal_note_instance(),
                    data=request.POST
                )
                if neonatal_note_form.is_valid():
                    return self.forms_valid(form, neonatal_note_form)
                return self.forms_invalid(form, neonatal_note_form)
            elif was_daily_note and hasattr(self.object, 'neonatal_daily_note'):
                self.object.neonatal_daily_note.delete()

            return self.form_valid(form)

        return self.form_invalid(form)

    def forms_valid(self, clinical_form, neonatal_note_form):
        with transaction.atomic():
            clinical_document = clinical_form.save()
            self.object = clinical_document

            neonatal_note = neonatal_note_form.save(commit=False)
            neonatal_note.document = clinical_document
            neonatal_note.save()

        return redirect(self.get_success_url())

    def forms_invalid(self, clinical_form, neonatal_note_form):
        return self.render_to_response(
            self.get_context_data(form=clinical_form, neonatal_note_form=neonatal_note_form)
        )

    def get_success_url(self):
        return self.request.GET.get('next') or reverse('documents:document_detail', kwargs={'pk': self.object.pk})


class DocumentDetailView(BaseDocumentView, DetailView):
    model = ClinicalDocument
    template_name = 'documents/detail.html'
    context_object_name = 'document'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Добавляем неонатальную запись, если она есть
        context['neonatal_note'] = getattr(self.object, 'neonatal_daily_note', None)

        return context


class DocumentDeleteView(BaseDocumentView, DeleteView):
    model = ClinicalDocument
    template_name = 'documents/confirm_delete.html'
    context_object_name = 'document'

    def get_success_url(self):
        return (
                self.request.GET.get('next')
                or self.get_dynamic_back_url(self.object)
        )


def template_data(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    return JsonResponse({
        'title': template.name,
        'content': template.default_content,
        'document_category_id': template.document_category.id if template.document_category else None # Возвращаем ID категории
    })