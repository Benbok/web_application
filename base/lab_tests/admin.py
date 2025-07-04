from django.contrib import admin
from .models import LabTestDefinition

@admin.register(LabTestDefinition)
class LabTestDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')