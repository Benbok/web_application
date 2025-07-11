from django.contrib import admin
from .models import NewbornProfile


@admin.register(NewbornProfile)
class NewbornProfileAdmin(admin.ModelAdmin):
    list_display = ('patient', 'gestational_age_weeks', 'gestational_age_days', 'birth_weight_grams', 'birth_height_cm', 'physical_development')
    list_filter = ('gestational_age_weeks', 'patient__gender')
    search_fields = ('patient__last_name', 'patient__first_name', 'patient__middle_name')
    readonly_fields = ('physical_development',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('patient', 'birth_time')
        }),
        ('Гестационный возраст', {
            'fields': ('gestational_age_weeks', 'gestational_age_days')
        }),
        ('Антропометрические данные', {
            'fields': ('birth_weight_grams', 'birth_height_cm', 'head_circumference_cm')
        }),
        ('Оценка по Апгар', {
            'fields': ('apgar_score_1_min', 'apgar_score_5_min', 'apgar_score_10_min')
        }),
        ('Медицинская информация', {
            'fields': ('notes', 'obstetric_history')
        }),
        ('Расчет физического развития', {
            'fields': ('physical_development',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')
