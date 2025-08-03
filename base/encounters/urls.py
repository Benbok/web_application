from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    path('<int:pk>/', views.EncounterDetailView.as_view(), name='encounter_detail'),
    path('add/<int:patient_pk>/', views.EncounterCreateView.as_view(), name='encounter_create'),
    path('<int:pk>/edit/', views.EncounterUpdateView.as_view(), name='encounter_update'),
    path('<int:pk>/delete/', views.EncounterDeleteView.as_view(), name='encounter_delete'),
    path('<int:pk>/close/', views.EncounterCloseView.as_view(), name='encounter_close'),
    path('<int:pk>/reopen/', views.EncounterReopenView.as_view(), name='encounter_reopen'),
    path('<int:pk>/undo/', views.EncounterUndoView.as_view(), name='encounter_undo'),
    
    # Диагнозы (старая версия)
    path('<int:pk>/diagnosis/', views.EncounterDiagnosisView.as_view(), name='encounter_diagnosis'),
    
    # Расширенная работа с диагнозами
    path('<int:pk>/diagnoses/', views.EncounterDiagnosisAdvancedView.as_view(), name='encounter_diagnosis_advanced'),
    path('<int:encounter_pk>/diagnoses/add/', views.EncounterDiagnosisCreateView.as_view(), name='encounter_diagnosis_create'),
    path('diagnoses/<int:pk>/edit/', views.EncounterDiagnosisUpdateView.as_view(), name='encounter_diagnosis_update'),
    path('diagnoses/<int:pk>/delete/', views.EncounterDiagnosisDeleteView.as_view(), name='encounter_diagnosis_delete'),
    
    # Планы лечения
    path('<int:encounter_pk>/treatment-plans/', views.TreatmentPlanListView.as_view(), name='treatment_plans'),
    path('<int:encounter_pk>/treatment-plans/add/', views.TreatmentPlanCreateView.as_view(), name='treatment_plan_create'),
    path('treatment-plans/<int:pk>/', views.TreatmentPlanDetailView.as_view(), name='treatment_plan_detail'),
    path('treatment-plans/<int:treatment_plan_pk>/medications/add/', views.TreatmentMedicationCreateView.as_view(), name='treatment_medication_create'),
    path('medications/<int:pk>/edit/', views.TreatmentMedicationUpdateView.as_view(), name='treatment_medication_update'),
    path('medications/<int:pk>/delete/', views.TreatmentMedicationDeleteView.as_view(), name='treatment_medication_delete'),
    path('plans/<int:plan_pk>/quick-add/<int:medication_id>/', views.QuickAddMedicationView.as_view(), name='quick_add_medication'),
    path('plans/<int:plan_pk>/quick-add-by-name/<str:medication_name>/', views.QuickAddMedicationView.as_view(), name='quick_add_medication_by_name'),
    
    # AJAX endpoints для схем лечения
    path('api/treatment-regimens/', views.TreatmentRegimensView.as_view(), name='treatment_regimens'),
    path('api/patient-recommendations/', views.PatientRecommendationsView.as_view(), name='patient_recommendations'),
]
