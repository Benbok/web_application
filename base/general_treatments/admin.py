from django.contrib import admin
from .models import GeneralTreatmentDefinition

@admin.register(GeneralTreatmentDefinition)
class GeneralTreatmentDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')