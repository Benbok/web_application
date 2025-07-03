from django.contrib import admin
from .models import MedicationAssignment, GeneralTreatmentAssignment, LabTestAssignment, InstrumentalProcedureAssignment

@admin.register(MedicationAssignment)
class MedicationAssignmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'assigning_doctor', 'medication', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'assigning_doctor', 'medication')
    search_fields = ('patient__full_name', 'medication__name', 'notes')
    ordering = ('-start_date',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(GeneralTreatmentAssignment)
class GeneralTreatmentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'assigning_doctor', 'general_treatment', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'assigning_doctor', 'general_treatment')
    search_fields = ('patient__full_name', 'general_treatment__name', 'notes')
    ordering = ('-start_date',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(LabTestAssignment)
class LabTestAssignmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'assigning_doctor', 'lab_test', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'assigning_doctor', 'lab_test')
    search_fields = ('patient__full_name', 'lab_test__name', 'notes')
    ordering = ('-start_date',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(InstrumentalProcedureAssignment)
class InstrumentalProcedureAssignmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'assigning_doctor', 'instrumental_procedure', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'assigning_doctor', 'instrumental_procedure')
    search_fields = ('patient__full_name', 'instrumental_procedure__name', 'notes')
    ordering = ('-start_date',)
    readonly_fields = ('created_at', 'updated_at')
