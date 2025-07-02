from django.contrib import admin
from .models import ClinicalDocument, DocumentTemplate, NeonatalDailyNote, DocumentAttachment, DocumentCategory
from django.urls import reverse
from django.utils.html import format_html

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_parent_name', 'department', 'is_leaf_node')
    list_filter = ('department', 'is_leaf_node', 'parent')
    search_fields = ('name',)
    # Используем raw_id_fields для ForeignKey 'parent',
    # если категорий может быть очень много.
    # Это позволяет вводить ID вместо выпадающего списка.
    raw_id_fields = ('parent',) 
    ordering = ('department__name', 'parent__name', 'name')

    fieldsets = (
        (None, {
            'fields': ('name', 'parent', 'department', 'is_leaf_node'),
        }),
    )

    def get_parent_name(self, obj):
        """Отображает имя родительской категории."""
        return obj.parent.name if obj.parent else "— (Корень)"
    get_parent_name.short_description = "Родительская категория"


# 3. Административная панель для модели DocumentTemplate
@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_category', 'is_global', 'author', 'created_at')
    list_filter = ('document_category', 'is_global', 'author', 'created_at')
    search_fields = ('name', 'default_content')
    # Используем raw_id_fields для ForeignKey 'author' и 'document_category'
    # для улучшения производительности при большом количестве пользователей/категорий.
    raw_id_fields = ('author', 'document_category')
    ordering = ('document_category__name', 'name')

    fieldsets = (
        (None, {
            'fields': ('name', 'document_category', 'default_content', 'is_global', 'author'),
        }),
    )

# Inline для вложений, если хотите управлять ими прямо из ClinicalDocument
class DocumentAttachmentInline(admin.TabularInline):
    model = DocumentAttachment
    extra = 1 # Количество пустых форм для добавления новых вложений


# Inline для NeonatalDailyNote, если хотите управлять им прямо из ClinicalDocument
# (Рекомендуется, так как это OneToOneField)
class NeonatalDailyNoteInline(admin.StackedInline):
    model = NeonatalDailyNote
    can_delete = True
    verbose_name_plural = 'Детали дневника новорожденного'
    # Максимальное количество форм для OneToOneField всегда 1
    max_num = 1
    # Поля, которые будут отображаться в инлайне
    fields = (
        'age_in_days', 'pkv',
        ('temperature', 'respiratory_rate', 'heart_rate'),
        ('blood_pressure_systolic', 'blood_pressure_diastolic', 'blood_pressure_mean', 'saturation', 'saturation_limb'),
        'respiratory_therapy_type', 'ventilator_device', 'ventilation_mode', 'respiratory_parameters',
        'severity_assessment', 'pathological_symptoms_dynamics',
        ('feeding_type', 'sucking_activity'),
        ('jaundice_kramer_scale', 'umbilical_cord_state', 'skin_state', 'eyes_state'),
        'respiratory_system_state', 'cardiovascular_system_state', 'gastrointestinal_features',
        ('stool_character', 'urination_character'),
        'conclusion', 'management_plan'
    )
    # Если вы хотите, чтобы инлайн появлялся только для определенной категории,
    # это сложнее сделать напрямую в админке, потребуется JavaScript.
    # По умолчанию он будет виден всегда, но пустым, если данных нет.


# 4. Административная панель для модели ClinicalDocument
@admin.register(ClinicalDocument)
class ClinicalDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_category_display', 'author', 'created_at', 'is_signed', 'is_canceled', 'link_to_parent')
    list_filter = ('document_category', 'author', 'is_signed', 'is_canceled', 'created_at')
    search_fields = ['document_category']
    # raw_id_fields для автора, шаблона и категории
    raw_id_fields = ('author', 'template', 'document_category')
    date_hierarchy = 'created_at' # Позволяет навигировать по датам
    ordering = ('-created_at',)
    inlines = [DocumentAttachmentInline, NeonatalDailyNoteInline] # Добавляем инлайны

    fieldsets = (
        (None, {
            'fields': ('document_category', 'template', 'author'),
        }),
        ('Связь с родительским объектом', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',), # Можно свернуть по умолчанию
        }),
        ('Статус документа', {
            'fields': ('is_signed', 'is_canceled'),
            'classes': ('collapse',),
        }),
    )
    
    # Сделаем поля content_type и object_id только для чтения,
    # так как они устанавливаются программно через GenericForeignKey.
    readonly_fields = ('content_type', 'object_id')

    def document_category_display(self, obj):
        """Отображает полный путь категории документа."""
        return obj.document_category.get_full_path() if obj.document_category else "Без категории"
    document_category_display.short_description = "Категория документа"

    def link_to_parent(self, obj):
        """
        Создает ссылку на родительский объект (например, на страницу пациента или случая).
        """
        if obj.content_object:
            content_type = obj.content_type
            object_id = obj.object_id
            try:
                # Попробуйте получить URL для админки родительского объекта
                url = reverse(f'admin:{content_type.app_label}_{content_type.model}_change', args=[object_id])
                return format_html('<a href="{}">{} ({})</a>', url, obj.content_object, content_type.model)
            except Exception:
                return f"{obj.content_object} ({content_type.model})"
        return "—"
    link_to_parent.short_description = "Связан с"


# 5. Административная панель для модели NeonatalDailyNote
# Если вы используете NeonatalDailyNoteInline в ClinicalDocumentAdmin,
# то этот @admin.register(NeonatalDailyNote) может быть необязательным,
# так как записи будут создаваться/редактироваться через ClinicalDocument.
# Однако, если вы хотите иметь прямой доступ к NeonatalDailyNote, оставьте его.
@admin.register(NeonatalDailyNote)
class NeonatalDailyNoteAdmin(admin.ModelAdmin):
    list_display = ('document_link', 'get_datetime_document', 'age_in_days', 'temperature', 'respiratory_rate', 'heart_rate')
    search_fields = ('severity_assessment', 'management_plan')
    raw_id_fields = ('document',) # Связь с ClinicalDocument

    fieldsets = (
        (None, {
            'fields': ('document', 'get_datetime_document', 'age_in_days', 'pkv'),
        }),
        ('Витальные показатели', {
            'fields': (
                ('temperature', 'respiratory_rate', 'heart_rate'),
                ('blood_pressure_systolic', 'blood_pressure_diastolic', 'blood_pressure_mean', 'saturation', 'saturation_limb'),
            ),
        }),
        ('Респираторная терапия', {
            'fields': ('respiratory_therapy_type', 'ventilator_device', 'ventilation_mode', 'respiratory_parameters'),
        }),
        ('Оценка состояния и динамика', {
            'fields': (
                'severity_assessment', 'pathological_symptoms_dynamics', 'feeding_type', 'sucking_activity',
                'jaundice_kramer_scale', 'umbilical_cord_state', 'skin_state', 'eyes_state',
                'respiratory_system_state', 'cardiovascular_system_state', 'gastrointestinal_features',
                ('stool_character', 'urination_character'),
            ),
        }),
        ('Заключение и план', {
            'fields': ('conclusion', 'management_plan'),
        }),
    )

    def get_datetime_document(self, obj):
        return obj.document.datetime_document if obj.document else "—"
    get_datetime_document.short_description = "Дата документа"

    def document_link(self, obj):
        """Создает ссылку на связанный ClinicalDocument."""
        if obj.document:
            url = reverse('admin:your_app_name_clinicaldocument_change', args=[obj.document.pk])
            return format_html('<a href="{}">{}</a>', url, obj.document.title)
        return "—"
    document_link.short_description = "Связанный документ"

# Также можно зарегистрировать DocumentAttachment, если не используется только Inline
# @admin.register(DocumentAttachment)
# class DocumentAttachmentAdmin(admin.ModelAdmin):
#     list_display = ('document', 'file', 'uploaded_at')
#     list_filter = ('uploaded_at',)
#     search_fields = ('document__title', 'file')
#     raw_id_fields = ('document',)
    
@admin.register(DocumentAttachment)
class DocumentAttachmentAdmin(admin.ModelAdmin):
    list_display = ('document', 'file', 'uploaded_at')
    search_fields = ('document__title', 'file')
    list_filter = ['uploaded_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('document')
    

