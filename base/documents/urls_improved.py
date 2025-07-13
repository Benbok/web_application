"""
Улучшенные URL-ы для модуля Documents
"""
from django.urls import path
from . import views_improved

app_name = 'documents'

urlpatterns = [
    # Основные URL-ы для документов
    path('select/<str:model_name>/<int:object_id>/', 
         views_improved.DocumentTypeSelectionView.as_view(), 
         name='select_document_type'),
    
    path('create/<str:model_name>/<int:object_id>/<int:document_type_id>/', 
         views_improved.DocumentCreateView.as_view(), 
         name='document_create'),
    
    path('detail/<int:pk>/', 
         views_improved.DocumentDetailView.as_view(), 
         name='document_detail'),
    
    path('update/<int:pk>/', 
         views_improved.DocumentUpdateView.as_view(), 
         name='document_update'),
    
    path('delete/<int:pk>/', 
         views_improved.DocumentDeleteView.as_view(), 
         name='document_delete'),
    
    # Поиск документов
    path('search/', 
         views_improved.DocumentSearchView.as_view(), 
         name='search'),
    
    # API для действий с документами
    path('api/<int:pk>/action/', 
         views_improved.DocumentAPIActionView.as_view(), 
         name='document_api_action'),
    
    # URL-ы для версий (если нужны отдельные представления)
    path('version/<int:version_id>/data/', 
         views_improved.DocumentVersionDataView.as_view(), 
         name='version_data'),
    
    # URL-ы для аудита (если нужны отдельные представления)
    path('audit/<int:log_id>/changes/', 
         views_improved.DocumentAuditChangesView.as_view(), 
         name='audit_changes'),
    
    # Управление шаблонами
    path('templates/', 
         views_improved.DocumentTemplateListView.as_view(), 
         name='template_list'),
    
    path('templates/create/', 
         views_improved.DocumentTemplateCreateView.as_view(), 
         name='template_create'),
    
    path('templates/<int:pk>/update/', 
         views_improved.DocumentTemplateUpdateView.as_view(), 
         name='template_update'),
    
    path('templates/<int:pk>/delete/', 
         views_improved.DocumentTemplateDeleteView.as_view(), 
         name='template_delete'),
    
    # Управление типами документов
    path('types/', 
         views_improved.DocumentTypeListView.as_view(), 
         name='type_list'),
    
    path('types/create/', 
         views_improved.DocumentTypeCreateView.as_view(), 
         name='type_create'),
    
    path('types/<int:pk>/update/', 
         views_improved.DocumentTypeUpdateView.as_view(), 
         name='type_update'),
    
    path('types/<int:pk>/delete/', 
         views_improved.DocumentTypeDeleteView.as_view(), 
         name='type_delete'),
    
    # Статистика и аналитика
    path('statistics/', 
         views_improved.DocumentStatisticsView.as_view(), 
         name='statistics'),
    
    # Экспорт документов
    path('export/<int:pk>/pdf/', 
         views_improved.DocumentExportPDFView.as_view(), 
         name='export_pdf'),
    
    path('export/<int:pk>/docx/', 
         views_improved.DocumentExportDOCXView.as_view(), 
         name='export_docx'),
] 