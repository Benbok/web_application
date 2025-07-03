from django.contrib import admin
from .models import DocumentType, ClinicalDocument, DocumentTemplate

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department')
    list_filter = ('department',)
    search_fields = ('name',)

@admin.register(ClinicalDocument)
class ClinicalDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'author', 'datetime_document', 'is_signed')
    list_filter = ('document_type', 'author', 'is_signed', 'datetime_document')
    search_fields = ('document_type__name', 'data')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_type', 'author', 'is_global')
    list_filter = ('document_type', 'author', 'is_global')
    search_fields = ('name', 'document_type__name')