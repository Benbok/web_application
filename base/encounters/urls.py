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
    
    # Планы лечения (перенаправляем на treatment_management)
    path('<int:encounter_pk>/treatment-plans/', views.redirect_to_treatment_management, name='treatment_plans'),
    path('<int:encounter_pk>/treatment-plans/add/', views.redirect_to_treatment_management, name='treatment_plan_create'),
    path('treatment-plans/<int:pk>/', views.redirect_to_treatment_management, name='treatment_plan_detail'),
    path('treatment-plans/<int:pk>/delete/', views.redirect_to_treatment_management, name='treatment_plan_delete'),
    path('treatment-plans/<int:treatment_plan_pk>/medications/add/', views.redirect_to_treatment_management, name='treatment_medication_create'),
    path('medications/<int:pk>/edit/', views.redirect_to_treatment_management, name='treatment_medication_update'),
    path('medications/<int:pk>/delete/', views.redirect_to_treatment_management, name='treatment_medication_delete'),
    path('plans/<int:plan_pk>/quick-add/<int:medication_id>/', views.redirect_to_treatment_management, name='quick_add_medication'),
    path('plans/<int:plan_pk>/quick-add-by-name/<str:medication_name>/', views.redirect_to_treatment_management, name='quick_add_medication_by_name'),
    
    # Лабораторные назначения
    path('plans/<int:plan_pk>/lab-tests/add/', views.TreatmentLabTestCreateView.as_view(), name='treatment_lab_test_create'),
    path('lab-tests/<int:pk>/edit/', views.TreatmentLabTestUpdateView.as_view(), name='treatment_lab_test_update'),
    path('lab-tests/<int:pk>/delete/', views.TreatmentLabTestDeleteView.as_view(), name='treatment_lab_test_delete'),
    
    # Планы обследования
    path('<int:encounter_pk>/examination-plans/', views.ExaminationPlanListView.as_view(), name='examination_plan_list'),
    path('<int:encounter_pk>/examination-plans/add/', views.ExaminationPlanCreateView.as_view(), name='examination_plan_create'),
    path('examination-plans/<int:pk>/edit/', views.ExaminationPlanUpdateView.as_view(), name='examination_plan_update'),
    path('examination-plans/<int:pk>/delete/', views.ExaminationPlanDeleteView.as_view(), name='examination_plan_delete'),
    path('examination-plans/<int:pk>/', views.ExaminationPlanDetailView.as_view(), name='examination_plan_detail'),
    
    # Лабораторные исследования в плане обследования
    path('examination-plans/<int:plan_pk>/lab-tests/add/', views.ExaminationLabTestCreateView.as_view(), name='examination_lab_test_create'),
    path('examination-lab-tests/<int:pk>/edit/', views.ExaminationLabTestUpdateView.as_view(), name='examination_lab_test_update'),
    path('examination-lab-tests/<int:pk>/delete/', views.ExaminationLabTestDeleteView.as_view(), name='examination_lab_test_delete'),
    
    # Инструментальные исследования в плане обследования
    path('examination-plans/<int:plan_pk>/instrumental/add/', views.ExaminationInstrumentalCreateView.as_view(), name='examination_instrumental_create'),
    path('examination-instrumental/<int:pk>/edit/', views.ExaminationInstrumentalUpdateView.as_view(), name='examination_instrumental_update'),
    path('examination-instrumental/<int:pk>/delete/', views.ExaminationInstrumentalDeleteView.as_view(), name='examination_instrumental_delete'),
    
    # AJAX endpoints удалены - теперь используется перенаправление на treatment_management
    
    # Тестирование
    path('test-js/', views.TestJavaScriptView.as_view(), name='test_js'),
]
