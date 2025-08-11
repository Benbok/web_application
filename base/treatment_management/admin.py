from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import TreatmentPlan, TreatmentMedication, TreatmentRecommendation


class TreatmentMedicationInline(admin.TabularInline):
    """
    Inline для отображения лекарств в плане лечения
    """
    model = TreatmentMedication
    extra = 0
    fields = ['medication', 'custom_medication', 'dosage', 'frequency', 'route', 'duration']
    readonly_fields = ['created_at', 'updated_at']


class TreatmentRecommendationInline(admin.TabularInline):
    """
    Inline для отображения рекомендаций в плане лечения
    """
    model = TreatmentRecommendation
    extra = 0
    fields = ['text']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    """
    Админ для планов лечения
    """
    list_display = ['name', 'owner_display', 'created_at', 'medications_count']
    list_filter = ['created_at', 'content_type']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TreatmentMedicationInline, TreatmentRecommendationInline]
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('name', 'description')
        }),
        (_('Владелец'), {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        (_('Метаданные'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def owner_display(self, obj):
        """Отображает владельца плана лечения"""
        return obj.get_owner_display()
    owner_display.short_description = _('Владелец')
    
    def medications_count(self, obj):
        """Отображает количество лекарств в плане"""
        return obj.medications.count()
    medications_count.short_description = _('Количество лекарств')


@admin.register(TreatmentMedication)
class TreatmentMedicationAdmin(admin.ModelAdmin):
    """
    Админ для лекарств в планах лечения
    """
    list_display = ['medication_name', 'treatment_plan', 'dosage', 'frequency', 'route', 'created_at']
    list_filter = ['route', 'created_at', 'treatment_plan__content_type']
    search_fields = ['medication__name', 'custom_medication', 'treatment_plan__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('treatment_plan', 'medication', 'custom_medication')
        }),
        (_('Параметры назначения'), {
            'fields': ('dosage', 'frequency', 'route', 'duration', 'instructions')
        }),
        (_('Метаданные'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def medication_name(self, obj):
        """Отображает название лекарства"""
        return obj.get_medication_name()
    medication_name.short_description = _('Лекарство')


@admin.register(TreatmentRecommendation)
class TreatmentRecommendationAdmin(admin.ModelAdmin):
    """
    Админ для рекомендаций в планах лечения
    """
    list_display = ['text_preview', 'treatment_plan', 'created_at']
    list_filter = ['created_at', 'treatment_plan__content_type']
    search_fields = ['text', 'treatment_plan__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('treatment_plan', 'text')
        }),
        (_('Метаданные'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def text_preview(self, obj):
        """Отображает превью текста рекомендации"""
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = _('Текст рекомендации')
