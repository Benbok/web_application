from django.contrib import admin
from .models import Patient

from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'last_name', 'first_name', 'middle_name',
        'birth_date', 'gender', 'phone', 'email',
        'created_at', 'updated_at'
    )
    search_fields = ('last_name', 'first_name', 'middle_name', 'phone', 'email', 'snils', 'insurance_policy_number')
    list_filter = ('gender', 'birth_date', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ("Личные данные", {
            'fields': ('last_name', 'first_name', 'middle_name', 'birth_date', 'gender')
        }),
        ("Контакты", {
            'fields': ('phone', 'email')
        }),
        ("Адреса", {
            'fields': ('registration_address', 'residential_address')
        }),
        ("Документы", {
            'fields': (
                'snils', 'insurance_policy_number', 'insurance_company',
                'passport_series', 'passport_number', 'passport_issued_by',
                'passport_issued_date', 'passport_department_code'
            )
        }),
        ("Представитель", {
            'fields': (
                'legal_representative_full_name',
                'legal_representative_relation',
                'legal_representative_contacts'
            )
        }),
        ("Служебная информация", {
            'fields': ('created_at', 'updated_at')
        }),
    )