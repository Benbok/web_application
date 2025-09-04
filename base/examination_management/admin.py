from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import ExaminationPlan, ExaminationLabTest, ExaminationInstrumental


@admin.register(ExaminationPlan)
class ExaminationPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'encounter', 'priority', 'is_archived', 'created_at']
    list_filter = ['priority', 'is_archived', 'created_at']
    search_fields = ['name', 'description', 'encounter__patient__full_name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['archive_selected', 'restore_selected']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'priority')
        }),
        ('Архивирование', {
            'fields': ('is_archived', 'archived_at', 'archived_by', 'archive_reason'),
            'classes': ('collapse',)
        }),
        ('Связи', {
            'fields': ('encounter',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def archive_selected(self, request, queryset):
        """Архивирует выбранные записи"""
        archived_count = 0
        for obj in queryset:
            if not obj.is_archived:
                try:
                    obj.archive(user=request.user, reason="Архивировано через админку")
                    archived_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при архивировании записи {obj.id}: {str(e)}")
        
        if archived_count > 0:
            messages.success(request, f"Успешно архивировано {archived_count} записей.")
        else:
            messages.warning(request, "Нет записей для архивирования.")
    
    archive_selected.short_description = "Архивировать выбранные записи"
    
    def restore_selected(self, request, queryset):
        """Восстанавливает выбранные записи из архива"""
        restored_count = 0
        for obj in queryset:
            if obj.is_archived:
                try:
                    obj.restore(user=request.user)
                    restored_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при восстановлении записи {obj.id}: {str(e)}")
        
        if restored_count > 0:
            messages.success(request, f"Успешно восстановлено {restored_count} записей.")
        else:
            messages.warning(request, "Нет записей для восстановления.")
    
    restore_selected.short_description = "Восстановить выбранные записи из архива"


@admin.register(ExaminationLabTest)
class ExaminationLabTestAdmin(admin.ModelAdmin):
    list_display = ['examination_plan', 'lab_test', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
    search_fields = ['examination_plan__name', 'lab_test__name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['archive_selected', 'restore_selected']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('examination_plan', 'lab_test', 'instructions')
        }),
        ('Архивирование', {
            'fields': ('is_archived', 'archived_at', 'archived_by', 'archive_reason'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def archive_selected(self, request, queryset):
        """Архивирует выбранные записи"""
        archived_count = 0
        for obj in queryset:
            if not obj.is_archived:
                try:
                    obj.archive(user=request.user, reason="Архивировано через админку")
                    archived_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при архивировании записи {obj.id}: {str(e)}")
        
        if archived_count > 0:
            messages.success(request, f"Успешно архивировано {archived_count} записей.")
        else:
            messages.warning(request, "Нет записей для архивирования.")
    
    archive_selected.short_description = "Архивировать выбранные записи"
    
    def restore_selected(self, request, queryset):
        """Восстанавливает выбранные записи из архива"""
        restored_count = 0
        for obj in queryset:
            if obj.is_archived:
                try:
                    obj.restore(user=request.user)
                    restored_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при восстановлении записи {obj.id}: {str(e)}")
        
        if restored_count > 0:
            messages.success(request, f"Успешно восстановлено {restored_count} записей.")
        else:
            messages.warning(request, "Нет записей для восстановления.")
    
    restore_selected.short_description = "Восстановить выбранные записи из архива"


@admin.register(ExaminationInstrumental)
class ExaminationInstrumentalAdmin(admin.ModelAdmin):
    list_display = ['examination_plan', 'instrumental_procedure', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
    search_fields = ['examination_plan__name', 'instrumental_procedure__name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['archive_selected', 'restore_selected']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('examination_plan', 'instrumental_procedure', 'instructions')
        }),
        ('Архивирование', {
            'fields': ('is_archived', 'archived_at', 'archived_by', 'archive_reason'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def archive_selected(self, request, queryset):
        """Архивирует выбранные записи"""
        archived_count = 0
        for obj in queryset:
            if not obj.is_archived:
                try:
                    obj.archive(user=request.user, reason="Архивировано через админку")
                    archived_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при архивировании записи {obj.id}: {str(e)}")
        
        if archived_count > 0:
            messages.success(request, f"Успешно архивировано {archived_count} записей.")
        else:
            messages.warning(request, "Нет записей для архивирования.")
    
    archive_selected.short_description = "Архивировать выбранные записи"
    
    def restore_selected(self, request, queryset):
        """Восстанавливает выбранные записи из архива"""
        restored_count = 0
        for obj in queryset:
            if obj.is_archived:
                try:
                    obj.restore(user=request.user)
                    restored_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при восстановлении записи {obj.id}: {str(e)}")
        
        if restored_count > 0:
            messages.success(request, f"Успешно восстановлено {restored_count} записей.")
        else:
            messages.warning(request, "Нет записей для восстановления.")
    
    restore_selected.short_description = "Восстановить выбранные записи из архива"
