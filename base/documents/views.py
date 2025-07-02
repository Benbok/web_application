# views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, reverse_lazy
from django.db import transaction

# Импортируем новые модели Department, DocumentCategory
from .models import ClinicalDocument, DocumentTemplate, NeonatalDailyNote, DocumentCategory
# Импортируем обновленные формы
from .forms import ClinicalDocumentForm, NeonatalDailyNoteForm


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
            return reverse('encounters:encounter_detail', kwargs={'pk': parent_obj.pk})
        elif content_type.model == 'patientdepartmentstatus':
            return reverse('departments:department_detail', kwargs={'pk': parent_obj.pk})
        elif content_type.model == 'treatmentassignment':
            return reverse('treatment_assignments:assignment_detail', kwargs={'pk': parent_obj.pk})
    
    return DEFAULT_DOCUMENT_LIST_URL

class DocumentDetailView(DetailView):
    model = ClinicalDocument
    template_name = 'documents/detail.html'
    context_object_name = 'document'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.object)
        
        # Если документ относится к категории "Дневник наблюдения новорожденного",
        # передаем его данные в контекст.
        # Необходимо получить конкретный объект DocumentCategory для "Ежедневный дневник"
        # или использовать его ID, если он известен и стабилен.
        # Для гибкости, можно проверять по имени категории или по полному пути.
        # Предполагаем, что "Ежедневный дневник" - это конкретная конечная категория.
        # В реальном приложении лучше получить ID этой категории при запуске сервера или из настроек.

        # Пример: поиск категории по имени (менее производительно, лучше по ID)
        # try:
        #     daily_note_category = DocumentCategory.objects.get(name="Ежедневный дневник", is_leaf_node=True)
        # except DocumentCategory.DoesNotExist:
        #     daily_note_category = None
        #
        # if daily_note_category and self.object.document_category == daily_note_category:
        #     try:
        #         context['neonatal_note'] = self.object.neonatal_daily_note
        #     except NeonatalDailyNote.DoesNotExist:
        #         context['neonatal_note'] = None
        # else:
        #     context['neonatal_note'] = None # Убедимся, что всегда есть значение, если нет дневника

        return context


class DocumentCreateView(CreateView):
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
        kwargs['user'] = self.request.user
        kwargs['parent_object'] = self.parent_object
        return kwargs

    def get_daily_note_category_id(self):
        try:
            return DocumentCategory.objects.get(name="Ежедневные дневники", is_leaf_node=True).id
        except DocumentCategory.DoesNotExist:
            return None

    def is_neonatology_department_and_daily_note(self, selected_category_id=None):
        # Проверяем, что родительский объект — статус пациента в отделении
        department = None
        if hasattr(self.parent_object, 'department'):
            department = getattr(self.parent_object, 'department', None)
        if not department or getattr(department, 'name', '').lower() != 'неонатология':
            return False
        daily_note_category_id = self.get_daily_note_category_id()
        if not daily_note_category_id:
            return False
        if selected_category_id is not None:
            return int(selected_category_id) == daily_note_category_id
        # Если категория не передана, не показываем форму
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новый документ'
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.parent_object)
        context['parent_object'] = self.parent_object
        daily_note_category_id = self.get_daily_note_category_id()
        context['daily_note_category_id'] = daily_note_category_id

        form = kwargs.get('form', context.get('form', self.get_form()))
        show_neonatal = False
        selected_category = None
        if form.is_bound:
            try:
                selected_category = int(form.data.get('document_category', 0))
            except (TypeError, ValueError):
                pass
        if selected_category and self.is_neonatology_department_and_daily_note(selected_category):
            show_neonatal = True
        context['show_neonatal_note_form'] = show_neonatal
        if show_neonatal:
            context['neonatal_note_form'] = kwargs.get('neonatal_note_form', NeonatalDailyNoteForm(self.request.POST or None))
        else:
            context['neonatal_note_form'] = None
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        selected_category = None
        try:
            selected_category = int(request.POST.get('document_category', 0))
        except (TypeError, ValueError):
            pass
        if form.is_valid():
            if selected_category and self.is_neonatology_department_and_daily_note(selected_category):
                neonatal_note_form = NeonatalDailyNoteForm(request.POST)
                if neonatal_note_form.is_valid():
                    return self.forms_valid(form, neonatal_note_form)
                else:
                    return self.forms_invalid(form, neonatal_note_form)
            else:
                return self.form_valid(form)
        else:
            if selected_category and self.is_neonatology_department_and_daily_note(selected_category):
                neonatal_note_form = NeonatalDailyNoteForm(request.POST)
                return self.forms_invalid(form, neonatal_note_form)
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
            self.get_context_data(
                form=clinical_form,
                neonatal_note_form=neonatal_note_form
            )
        )

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        self.object.content_object = self.parent_object
        self.object.save()
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_success_url(self):
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
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['parent_object'] = self.object.content_object # Передаем parent_object в форму
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактировать документ'
        context['next_url'] = self.request.GET.get('next', '')
        context['default_back_url'] = get_dynamic_back_url(self.object)
        context['parent_object'] = self.object.content_object
        
        # Если документ относится к категории "Ежедневный дневник", инициализируем NeonatalDailyNoteForm
        # Сначала получаем ID этой категории
        daily_note_category_id = None
        try:
            daily_note_category_id = DocumentCategory.objects.get(name="Ежедневный дневник", is_leaf_node=True).id
        except DocumentCategory.DoesNotExist:
            pass
        
        if daily_note_category_id and self.object.document_category and \
           self.object.document_category.id == daily_note_category_id:
            try:
                neonatal_note_instance = self.object.neonatal_daily_note
            except NeonatalDailyNote.DoesNotExist:
                neonatal_note_instance = None
            
            if 'neonatal_note_form' not in kwargs:
                context['neonatal_note_form'] = NeonatalDailyNoteForm(instance=neonatal_note_instance)
        else:
            context['neonatal_note_form'] = None # Явно устанавливаем None, если не дневник

        context['daily_note_category_id'] = daily_note_category_id # Передаем ID категории для JS

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        daily_note_category_id = None
        try:
            daily_note_category_id = DocumentCategory.objects.get(name="Ежедневный дневник", is_leaf_node=True).id
        except DocumentCategory.DoesNotExist:
            pass

        if form.is_valid():
            new_document_category = form.cleaned_data['document_category']
            
            # Проверяем, была ли старая категория "Дневником новорожденного"
            was_daily_note = False
            if self.object.document_category and daily_note_category_id and \
               self.object.document_category.id == daily_note_category_id:
                was_daily_note = True

            # Проверяем, будет ли новая категория "Дневником новорожденного"
            is_daily_note_now = False
            if new_document_category and daily_note_category_id and \
               new_document_category.id == daily_note_category_id:
                is_daily_note_now = True

            if is_daily_note_now:
                try:
                    neonatal_note_instance = self.object.neonatal_daily_note
                except NeonatalDailyNote.DoesNotExist:
                    neonatal_note_instance = None

                neonatal_note_form = NeonatalDailyNoteForm(request.POST, instance=neonatal_note_instance)
                if neonatal_note_form.is_valid():
                    return self.forms_valid(form, neonatal_note_form)
                else:
                    return self.forms_invalid(form, neonatal_note_form)
            else:
                # Если тип документа изменился с "Дневника новорожденного" на что-то другое,
                # или изначально не был дневником и не стал им.
                if was_daily_note and hasattr(self.object, 'neonatal_daily_note'):
                    self.object.neonatal_daily_note.delete()
                return self.form_valid(form)
        else:
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
        # Добавляем ID категории "Ежедневный дневник" в контекст для JavaScript при ошибке
        try:
            daily_note_category_id = DocumentCategory.objects.get(name="Ежедневный дневник", is_leaf_node=True).id
        except DocumentCategory.DoesNotExist:
            daily_note_category_id = None

        return self.render_to_response(
            self.get_context_data(
                form=clinical_form, 
                neonatal_note_form=neonatal_note_form,
                daily_note_category_id=daily_note_category_id
            )
        )

    def form_valid(self, form):
        self.object = form.save()
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # Добавляем ID категории "Ежедневный дневник" в контекст для JavaScript при ошибке
        try:
            daily_note_category_id = DocumentCategory.objects.get(name="Ежедневный дневник", is_leaf_node=True).id
        except DocumentCategory.DoesNotExist:
            daily_note_category_id = None

        return self.render_to_response(
            self.get_context_data(
                form=form, 
                daily_note_category_id=daily_note_category_id
            )
        )

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
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return get_dynamic_back_url(self.object)


def template_data(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    return JsonResponse({
        'title': template.name,
        'content': template.default_content,
        'document_category_id': template.document_category.id if template.document_category else None # Возвращаем ID категории
    })