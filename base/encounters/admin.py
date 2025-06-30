from django.contrib import admin
from .models import Encounter

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date_start', 'date_end', 'is_active')
    list_filter = ('is_active', 'doctor')
    search_fields = ('patient__family', 'patient__given', 'patient__middle')
    date_hierarchy = 'date_start'
    ordering = ('-date_start',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'doctor')