from django.contrib import admin
from .models import InstrumentalProcedureDefinition

@admin.register(InstrumentalProcedureDefinition)
class InstrumentalProcedureDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')