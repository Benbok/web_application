from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import LabTestDefinition, LabTestResult


@admin.register(LabTestDefinition)
class LabTestDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'has_schema')
    search_fields = ('name', 'description')
    list_filter = ('name',)
    ordering = ('name',)
    
    def has_schema(self, obj):
        """Показывает, есть ли схема полей у определения теста"""
        return bool(obj.schema)
    has_schema.boolean = True
    has_schema.short_description = 'Есть схема'


@admin.register(LabTestResult)
class LabTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'patient_link', 'procedure_type', 'datetime_result', 
        'author_info', 'is_completed', 'examination_plan_link', 'created_at'
    )
    list_filter = (
        'is_completed', 'datetime_result', 'created_at', 
        'procedure_definition__name', 'examination_plan__name'
    )
    search_fields = (
        'patient__first_name', 'patient__last_name', 'patient__middle_name',
        'procedure_definition__name', 'examination_plan__name'
    )
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'datetime_result'
    ordering = ('-datetime_result',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('patient', 'procedure_definition', 'examination_plan')
        }),
        ('Результат', {
            'fields': ('datetime_result', 'data', 'is_completed', 'author')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_link(self, obj):
        """Ссылка на пациента"""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
        return '-'
    patient_link.short_description = 'Пациент'
    patient_link.admin_order_field = 'patient__last_name'
    
    def procedure_type(self, obj):
        """Тип процедуры с описанием"""
        if obj.procedure_definition:
            return format_html(
                '<strong>{}</strong><br><small class="text-muted">{}</small>',
                obj.procedure_definition.name,
                obj.procedure_definition.description or 'Без описания'
            )
        return '-'
    procedure_type.short_description = 'Тип исследования'
    procedure_type.admin_order_field = 'procedure_definition__name'
    
    def author_info(self, obj):
        """Информация об авторе"""
        if obj.author:
            return format_html(
                '<strong>{}</strong><br><small class="text-muted">{}</small>',
                obj.author.get_full_name() or obj.author.username,
                obj.author.email or 'Email не указан'
            )
        return '-'
    author_info.short_description = 'Автор'
    author_info.admin_order_field = 'author__last_name'
    
    def examination_plan_link(self, obj):
        """Ссылка на план обследования"""
        if obj.examination_plan:
            url = reverse('admin:examination_management_examinationplan_change', args=[obj.examination_plan.id])
            return format_html('<a href="{}">{}</a>', url, obj.examination_plan.name)
        return '-'
    examination_plan_link.short_description = 'План обследования'
    examination_plan_link.admin_order_field = 'examination_plan__name'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related(
            'patient', 'procedure_definition', 'examination_plan', 'author'
        )
    
    def has_add_permission(self, request):
        """Разрешаем добавление результатов"""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Разрешаем редактирование результатов"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление результатов"""
        return True
    
    def has_view_permission(self, request, obj=None):
        """Разрешаем просмотр результатов"""
        return True


# Настройки админки
admin.site.site_header = 'Администрирование медицинской системы'
admin.site.site_title = 'МедКарта - Админка'
admin.site.index_title = 'Управление медицинскими данными'