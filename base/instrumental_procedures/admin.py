from django.contrib import admin
from .models import InstrumentalProcedureDefinition, InstrumentalProcedureResult

@admin.register(InstrumentalProcedureDefinition)
class InstrumentalProcedureDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')

@admin.register(InstrumentalProcedureResult)
class InstrumentalProcedureResultAdmin(admin.ModelAdmin):
    list_display = ('patient', 'procedure_definition', 'author', 'datetime_result')
    list_filter = ('procedure_definition', 'author', 'datetime_result')
    search_fields = ('patient__first_name', 'patient__last_name', 'procedure_definition__name', 'author__username', 'data')
    raw_id_fields = ('patient', 'author')