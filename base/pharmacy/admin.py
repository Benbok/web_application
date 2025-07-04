from django.contrib import admin
from .models import Medication

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_dosage', 'unit', 'form')
    search_fields = ('name', 'default_dosage', 'unit', 'form')
    list_filter = ('unit', 'form')