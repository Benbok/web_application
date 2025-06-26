from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'date_of_birth')
    search_fields = ('full_name',)
    list_filter = ('date_of_birth',)