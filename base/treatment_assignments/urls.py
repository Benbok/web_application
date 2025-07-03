# treatment_assignments/urls.py
from django.urls import path
from . import views

app_name = 'treatment_assignments'

urlpatterns = [
    path('', views.TreatmentAssignmentListView.as_view(), name='assignment_list'),
    path('<int:pk>/', views.TreatmentAssignmentDetailView.as_view(), name='assignment_detail'),
    path('create/medication/<str:model_name>/<int:object_id>/', views.MedicationAssignmentCreateView.as_view(), name='medication_assignment_create'),
    path('create/general/<str:model_name>/<int:object_id>/', views.GeneralTreatmentAssignmentCreateView.as_view(), name='general_assignment_create'),
    path('create/lab/<str:model_name>/<int:object_id>/', views.LabTestAssignmentCreateView.as_view(), name='lab_assignment_create'),
    path('create/instrumental/<str:model_name>/<int:object_id>/', views.InstrumentalProcedureAssignmentCreateView.as_view(), name='instrumental_assignment_create'),
    path('<int:pk>/update/', views.TreatmentAssignmentUpdateView.as_view(), name='assignment_update'),
    path('<int:pk>/delete/', views.TreatmentAssignmentDeleteView.as_view(), name='assignment_delete'),
    path('daily-plan/<str:model_name>/<int:object_id>/', views.DailyTreatmentPlanView.as_view(), name='daily_plan'),
]