from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    path('<int:pk>/', views.EncounterDetailView.as_view(), name='encounter_detail'),
    path('add/<int:patient_pk>/', views.EncounterCreateView.as_view(), name='encounter_create'),
    path('<int:pk>/edit/', views.EncounterUpdateView.as_view(), name='encounter_update'),
    
    # Диагнозы (старая версия)
    path('<int:pk>/diagnosis/', views.EncounterDiagnosisView.as_view(), name='encounter_diagnosis'),
    
    # Расширенная работа с диагнозами
    path('<int:pk>/diagnoses/', views.EncounterDiagnosisAdvancedView.as_view(), name='encounter_diagnosis_advanced'),
    path('<int:encounter_pk>/diagnoses/add/', views.EncounterDiagnosisAdvancedCreateView.as_view(), name='encounter_diagnosis_create'),
    path('diagnoses/<int:pk>/edit/', views.EncounterDiagnosisAdvancedUpdateView.as_view(), name='encounter_diagnosis_update'),
    path('diagnoses/<int:pk>/delete/', views.EncounterDiagnosisAdvancedDeleteView.as_view(), name='encounter_diagnosis_delete'),
    
    # Действия с обращениями
    path('<int:pk>/close/', views.EncounterCloseView.as_view(), name='encounter_close'),
    path('<int:pk>/reopen/', views.EncounterReopenView.as_view(), name='encounter_reopen'),
    path('<int:pk>/delete/', views.EncounterDeleteView.as_view(), name='encounter_delete'),
]
