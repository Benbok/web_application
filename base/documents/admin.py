from django.contrib import admin
from .models import ClinicalDocument, DocumentTemplate

@admin.register(ClinicalDocument)
class ClinicalDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'created_at', 'author')
    search_fields = ('title', 'content')
    list_filter = ('document_type', 'created_at')
    
@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_type', 'is_global', 'author', 'created_at')
    search_fields = ('name', 'default_content')
    list_filter = ('document_type', 'is_global', 'author', 'created_at')    
    

