from django.contrib import admin
from .models import Diagnosis


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    list_filter = ('code',)
    search_fields = ('code', 'name')
    ordering = ('code',)
    list_per_page = 50 