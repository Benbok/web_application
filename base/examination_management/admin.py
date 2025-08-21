from django.contrib import admin
from .models import ExaminationPlan, ExaminationLabTest, ExaminationInstrumental


@admin.register(ExaminationPlan)
class ExaminationPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'encounter', 'priority', 'is_active', 'created_at']
    list_filter = ['priority', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'encounter__patient__full_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'priority', 'is_active')
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
    list_display = ['examination_plan', 'lab_test', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['examination_plan__name', 'lab_test__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('examination_plan', 'lab_test', 'status', 'instructions')
        }),
        ('Статус', {
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason', 'paused_at', 'paused_by', 'pause_reason', 'completed_at', 'completed_by', 'completion_notes'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExaminationInstrumental)
class ExaminationInstrumentalAdmin(admin.ModelAdmin):
    list_display = ['examination_plan', 'instrumental_procedure', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['examination_plan__name', 'instrumental_procedure__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('examination_plan', 'instrumental_procedure', 'status', 'instructions')
        }),
        ('Статус', {
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason', 'paused_at', 'paused_by', 'pause_reason', 'completed_at', 'completed_by', 'completion_notes'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
