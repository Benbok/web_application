from django.contrib import admin
from .models import TreatmentAssignment

@admin.register(TreatmentAssignment)
class TreatmentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'assigning_doctor', 'medication', 'status')
    list_filter = ('status', 'assigning_doctor')
    search_fields = ('patient__full_name', 'medication__name')
    ordering = ('-assignment_date',)
    readonly_fields = ('assignment_date', 'created_at', 'updated_at')
