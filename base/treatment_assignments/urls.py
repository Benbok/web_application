# treatment_assignments/urls.py
from django.urls import path
from . import views

app_name = 'treatment_assignments'

urlpatterns = [
    path('', views.TreatmentAssignmentListView.as_view(), name='assignment_list'),
    path('<int:pk>/', views.TreatmentAssignmentDetailView.as_view(), name='assignment_detail'),
    path('create/<str:model_name>/<int:object_id>/', views.TreatmentAssignmentCreateView.as_view(), name='assignment_create'),
    path('<int:pk>/update/', views.TreatmentAssignmentUpdateView.as_view(), name='assignment_update'),
    path('<int:pk>/delete/', views.TreatmentAssignmentDeleteView.as_view(), name='assignment_delete'),
]