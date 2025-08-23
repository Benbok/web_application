from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import DocumentSignature, SignatureWorkflow, SignatureTemplate


@admin.register(SignatureWorkflow)
class SignatureWorkflowAdmin(admin.ModelAdmin):
    """Админка для рабочих процессов подписей"""
    list_display = [
        'name', 'workflow_type', 'is_active', 'created_at', 
        'get_signature_count', 'get_pending_count'
    ]
    list_filter = ['workflow_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'workflow_type', 'description', 'is_active')
        }),
        ('Требуемые подписи', {
            'fields': (
                'require_doctor_signature', 'require_head_signature',
                'require_chief_signature', 'require_patient_signature'
            )
        }),
        ('Автоматические действия', {
            'fields': (
                'auto_complete_on_doctor_signature', 'auto_complete_on_all_signatures'
            )
        }),
        ('Временные ограничения (дни)', {
            'fields': (
                'doctor_signature_timeout_days', 'head_signature_timeout_days',
                'chief_signature_timeout_days', 'patient_signature_timeout_days'
            )
        }),
        ('Дополнительные настройки', {
            'fields': ('allow_parallel_signatures', 'require_sequential_order')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Добавляем предупреждение о связанных объектах"""
        if obj and obj.signatures.exists():
            return ['created_at', 'updated_at', 'related_signatures_warning']
        return ['created_at', 'updated_at']
    
    def related_signatures_warning(self, obj):
        """Предупреждение о связанных подписях"""
        if obj.signatures.exists():
            count = obj.signatures.count()
            return format_html(
                '<div style="color: red; font-weight: bold; padding: 10px; border: 1px solid red; background-color: #ffe6e6;">'
                '⚠️ ВНИМАНИЕ: Этот рабочий процесс связан с {} подписями. '
                'При удалении все связанные подписи будут также удалены!</div>',
                count
            )
        return ""
    related_signatures_warning.short_description = "Предупреждение"
    
    def get_signature_count(self, obj):
        """Количество всех подписей для этого процесса"""
        count = DocumentSignature.objects.filter(workflow=obj).count()
        return count
    get_signature_count.short_description = 'Всего подписей'
    
    def get_pending_count(self, obj):
        """Количество ожидающих подписей"""
        count = DocumentSignature.objects.filter(workflow=obj, status='pending').count()
        if count > 0:
            return format_html('<span style="color: orange;">{}</span>', count)
        return count
    get_pending_count.short_description = 'Ожидают подписи'
    
    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление рабочих процессов только администраторам"""
        return request.user.is_superuser
    
    def delete_model(self, request, obj):
        """Переопределяем удаление для логирования"""
        signature_count = obj.signatures.count()
        if signature_count > 0:
            print(f"Удаление рабочего процесса '{obj.name}' с {signature_count} связанными подписями")
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Переопределяем массовое удаление для логирования"""
        for obj in queryset:
            signature_count = obj.signatures.count()
            if signature_count > 0:
                print(f"Массовое удаление: рабочий процесс '{obj.name}' с {signature_count} связанными подписями")
        super().delete_queryset(request, queryset)


@admin.register(DocumentSignature)
class DocumentSignatureAdmin(admin.ModelAdmin):
    """Админка для подписей документов"""
    list_display = [
        'id', 'get_document_info', 'signature_type', 'status', 
        'required_signer', 'actual_signer', 'workflow', 'created_at'
    ]
    list_filter = [
        'signature_type', 'status', 'workflow', 'created_at', 'signed_at'
    ]
    search_fields = [
        'required_signer__username', 'required_signer__first_name', 
        'required_signer__last_name', 'actual_signer__username',
        'signature_notes', 'notes'
    ]
    readonly_fields = [
        'content_type', 'object_id', 'workflow', 'signature_type',
        'required_signer', 'actual_signer', 'signature_hash',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('content_type', 'object_id', 'workflow', 'signature_type')
        }),
        ('Статус и участники', {
            'fields': ('status', 'required_signer', 'actual_signer')
        }),
        ('Данные подписи', {
            'fields': ('signature_notes', 'signature_hash')
        }),
        ('Комментарии и причины', {
            'fields': ('notes', 'rejection_reason', 'cancellation_reason')
        }),
        ('Временные метки', {
            'fields': ('required_by', 'signed_at', 'created_at', 'updated_at')
        }),
    )
    
    def get_document_info(self, obj):
        """Информация о документе"""
        try:
            document = obj.content_object
            if document:
                # Создаем ссылку на документ в админке
                app_label = obj.content_type.app_label
                model_name = obj.content_type.model
                
                # Пытаемся найти URL для редактирования в админке
                try:
                    admin_url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.object_id])
                    return format_html(
                        '<a href="{}" target="_blank">{}</a>',
                        admin_url,
                        f"{app_label}.{model_name} #{obj.object_id}"
                    )
                except:
                    return f"{app_label}.{model_name} #{obj.object_id}"
            else:
                return f"Документ не найден ({obj.content_type.app_label}.{obj.content_type.model} #{obj.object_id})"
        except Exception as e:
            return f"Ошибка: {e}"
    
    get_document_info.short_description = 'Документ'
    get_document_info.admin_order_field = 'content_type'
    
    def get_queryset(self, request):
        """Оптимизируем запросы"""
        return super().get_queryset(request).select_related(
            'content_type', 'workflow', 'required_signer', 'actual_signer'
        )
    
    def has_add_permission(self, request):
        """Запрещаем создание подписей вручную через админку"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Разрешаем только просмотр и редактирование статуса"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление подписей только администраторам"""
        return request.user.is_superuser


@admin.register(SignatureTemplate)
class SignatureTemplateAdmin(admin.ModelAdmin):
    """Админка для шаблонов подписей"""
    list_display = [
        'name', 'workflow', 'auto_apply', 'is_active', 
        'get_content_types_count', 'created_at'
    ]
    list_filter = ['auto_apply', 'is_active', 'workflow', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'workflow', 'is_active')
        }),
        ('Настройки применения', {
            'fields': ('content_types', 'auto_apply')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_content_types_count(self, obj):
        """Количество типов контента для шаблона"""
        count = obj.content_types.count()
        return count
    get_content_types_count.short_description = 'Типов документов'
    
    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление шаблонов только администраторам"""
        return request.user.is_superuser
    
    def delete_model(self, request, obj):
        """Переопределяем удаление для логирования"""
        content_types_count = obj.content_types.count()
        print(f"Удаление шаблона подписи '{obj.name}' с {content_types_count} типами документов")
        super().delete_model(request, obj)


# Дополнительные настройки админки
admin.site.site_header = "Администрирование системы подписей"
admin.site.site_title = "Система подписей"
admin.site.index_title = "Управление подписями документов"
