from django.urls import path
from . import views

app_name = 'document_signatures'

urlpatterns = [
    # Основные страницы подписей
    path('', views.SignatureListView.as_view(), name='signature_list'),
    path('dashboard/', views.SignatureDashboardView.as_view(), name='dashboard'),
    
    # Управление подписями
    path('signatures/', views.SignatureListView.as_view(), name='signature_list'),
    path('signatures/<int:pk>/', views.SignatureDetailView.as_view(), name='signature_detail'),
    path('signatures/<int:pk>/sign/', views.SignatureSignView.as_view(), name='signature_sign'),
    path('signatures/<int:pk>/reject/', views.SignatureRejectView.as_view(), name='signature_reject'),
    path('signatures/<int:pk>/cancel/', views.SignatureCancelView.as_view(), name='signature_cancel'),
    
    # Просмотр подписей для документа
    path('document/<int:content_type_id>/<int:object_id>/', 
         views.DocumentSignaturesView.as_view(), name='document_signatures'),
    
    # API для AJAX запросов
    path('api/<int:content_type_id>/<int:object_id>/', 
         views.SignatureAPIView.as_view(), name='signature_api'),
    
    # Управление рабочими процессами
    path('workflows/', views.SignatureWorkflowListView.as_view(), name='workflow_list'),
    path('workflows/<int:pk>/', views.SignatureWorkflowDetailView.as_view(), name='workflow_detail'),
    path('workflows/create/', views.SignatureWorkflowCreateView.as_view(), name='workflow_create'),
    path('workflows/<int:pk>/edit/', views.SignatureWorkflowUpdateView.as_view(), name='workflow_edit'),
    
    # Управление шаблонами
    path('templates/', views.SignatureTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.SignatureTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.SignatureTemplateUpdateView.as_view(), name='template_edit'),
] 