from django.contrib import admin
from .models import ExaminationPlan, ExaminationLabTest, ExaminationInstrumental


@admin.register(ExaminationPlan)
class ExaminationPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'encounter', 'priority', 'is_archived', 'created_at']
    list_filter = ['priority', 'is_archived', 'created_at']
    search_fields = ['name', 'description', 'encounter__patient__full_name']
    readonly_fields = ['created_at', 'updated_at']
    
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


@admin.register(ExaminationLabTest)
class ExaminationLabTestAdmin(admin.ModelAdmin):
    list_display = ['examination_plan', 'lab_test', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
    search_fields = ['examination_plan__name', 'lab_test__name']
    readonly_fields = ['created_at', 'updated_at']
    
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


@admin.register(ExaminationInstrumental)
class ExaminationInstrumentalAdmin(admin.ModelAdmin):
    list_display = ['examination_plan', 'instrumental_procedure', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
    search_fields = ['examination_plan__name', 'instrumental_procedure__name']
    readonly_fields = ['created_at', 'updated_at']
    
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
