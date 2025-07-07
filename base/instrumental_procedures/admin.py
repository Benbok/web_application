from django.contrib import admin
from .models import InstrumentalProcedureDefinition, InstrumentalProcedureResult

@admin.register(InstrumentalProcedureDefinition)
class InstrumentalProcedureDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')

@admin.register(InstrumentalProcedureResult)
class InstrumentalProcedureResultAdmin(admin.ModelAdmin):
    list_display = ('instrumental_procedure_assignment', 'procedure_definition', 'author', 'datetime_result')
    list_filter = ('procedure_definition', 'author', 'datetime_result')
    search_fields = ('instrumental_procedure_assignment__instrumental_procedure__name', 'author__username', 'data')
    raw_id_fields = ('instrumental_procedure_assignment', 'author')