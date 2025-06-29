from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('<int:pk>/', views.document_detail, name='document_detail'),
    path('add/<int:encounter_pk>/', views.document_create, name='document_create'),
    path('<int:pk>/edit/', views.document_update, name='document_update'),
    path('<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('template-data/<int:pk>/', views.template_data, name='template_data'),
]