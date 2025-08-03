from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    path('<int:pk>/', views.EncounterDetailView.as_view(), name='encounter_detail'),
    path('add/<int:patient_pk>/', views.EncounterCreateView.as_view(), name='encounter_create'),
    path('<int:pk>/edit/', views.EncounterUpdateView.as_view(), name='encounter_update'),
    path('<int:pk>/diagnosis/', views.EncounterDiagnosisView.as_view(), name='encounter_diagnosis'),
    path('<int:pk>/delete/', views.EncounterDeleteView.as_view(), name='encounter_delete'),
    path('<int:pk>/close/', views.EncounterCloseView.as_view(), name='encounter_close'),
    path('<int:pk>/reopen/', views.EncounterReopenView.as_view(), name='encounter_reopen'),
    path('<int:pk>/undo/', views.EncounterUndoView.as_view(), name='encounter_undo'),
    
    # AJAX endpoints для схем лечения
    path('api/treatment-regimens/', views.TreatmentRegimensView.as_view(), name='treatment_regimens'),
    path('api/patient-recommendations/', views.PatientRecommendationsView.as_view(), name='patient_recommendations'),
]
