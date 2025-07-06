from django.contrib import admin
from .models import Patient, PatientContact, PatientAddress, PatientDocument


class PatientContactInline(admin.StackedInline):
    model = PatientContact
    extra = 0


class PatientAddressInline(admin.StackedInline):
    model = PatientAddress
    extra = 0


class PatientDocumentInline(admin.StackedInline):
    model = PatientDocument
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'birth_date', 'gender', 'patient_type')
    search_fields = ('last_name', 'first_name', 'middle_name')
    inlines = [PatientContactInline, PatientAddressInline, PatientDocumentInline]
