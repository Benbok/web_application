from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('select-type/<str:model_name>/<int:object_id>/', views.DocumentTypeSelectionView.as_view(), name='document_type_selection'),
    path('add/<str:model_name>/<int:object_id>/<int:document_type_id>/', views.DocumentCreateView.as_view(), name='document_create'),
    path('<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('<int:pk>/update/', views.DocumentUpdateView.as_view(), name='document_update'), # Добавляем обратно этот URL
    # URL-ы для удаления можно будет добавить позже
    path('<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
]