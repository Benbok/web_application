# a_refactored_example/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Для CBV нужно вызывать метод .as_view()
    path('<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('add/<str:model_name>/<int:object_id>/', views.DocumentCreateView.as_view(), name='document_create'),
    path('<int:pk>/edit/', views.DocumentUpdateView.as_view(), name='document_update'),
    path('<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
    
    # Эта ссылка остается без изменений, т.к. view остался функцией
    path('template-data/<int:pk>/', views.template_data, name='template_data'),
]