from django.urls import path
from . import views

app_name = 'examination_management'

urlpatterns = [
    # Специальные URL для encounters (для обратной совместимости)
    path('encounters/<int:encounter_pk>/plans/', 
         views.ExaminationPlanListView.as_view(), 
         name='examination_plan_list'),
    
    path('encounters/<int:encounter_pk>/plans/create/', 
         views.ExaminationPlanCreateView.as_view(), 
         name='examination_plan_create'),
    
    # Быстрое создание/открытие основного плана для encounter
    path('encounters/<int:encounter_pk>/plans/quick/',
         views.ExaminationPlanQuickCreateView.as_view(),
         name='examination_plan_quick'),
    
    path('encounters/<int:encounter_pk>/plans/<int:pk>/', 
         views.ExaminationPlanDetailView.as_view(), 
         name='examination_plan_detail'),
    

    
    path('encounters/<int:encounter_pk>/plans/<int:pk>/delete/', 
         views.ExaminationPlanDeleteView.as_view(), 
         name='examination_plan_delete'),
    
    # Общие URL-паттерны для других типов владельцев
    path('<str:owner_model>/<int:owner_id>/plans/', 
         views.ExaminationPlanListView.as_view(), 
         name='plan_list'),
    
    path('<str:owner_model>/<int:owner_id>/plans/create/', 
         views.ExaminationPlanCreateView.as_view(), 
         name='plan_create'),
    
    path('<str:owner_model>/<int:owner_id>/plans/<int:pk>/', 
         views.ExaminationPlanDetailView.as_view(), 
         name='plan_detail'),
    

    
    path('<str:owner_model>/<int:owner_id>/plans/<int:pk>/delete/', 
         views.ExaminationPlanDeleteView.as_view(), 
         name='plan_delete'),
    
    # Лабораторные исследования в планах обследования
    path('plans/<int:plan_pk>/lab-tests/add/', 
         views.ExaminationLabTestCreateView.as_view(), 
         name='lab_test_create'),
    
    # Просмотр результатов лабораторных исследований
    path('lab-tests/<int:pk>/result/', 
         views.LabTestResultView.as_view(), 
         name='lab_test_result_view'),
    
    # Управление статусами лабораторных исследований
    path('lab-tests/<int:pk>/status/complete/', 
         views.ExaminationLabTestCompleteView.as_view(), 
         name='lab_test_complete'),
    
    path('lab-tests/<int:pk>/status/reject/', 
         views.ExaminationLabTestRejectView.as_view(), 
         name='lab_test_reject'),
    
    path('lab-tests/<int:pk>/status/pause/', 
         views.ExaminationLabTestPauseView.as_view(), 
         name='lab_test_pause'),
    
    path('lab-tests/<int:pk>/edit/', 
         views.ExaminationLabTestUpdateView.as_view(), 
         name='lab_test_update'),
    
    path('lab-tests/<int:pk>/cancel/', 
         views.ExaminationLabTestCancelView.as_view(), 
         name='lab_test_cancel'),
    
    path('lab-tests/<int:pk>/delete/', 
         views.ExaminationLabTestDeleteView.as_view(), 
         name='lab_test_delete'),
    
    # Инструментальные исследования в планах обследования
    path('plans/<int:plan_pk>/instrumental/add/', 
         views.ExaminationInstrumentalCreateView.as_view(), 
         name='instrumental_create'),
    
    # Просмотр результатов инструментальных исследований
    path('instrumental/<int:pk>/result/', 
         views.InstrumentalResultView.as_view(), 
         name='instrumental_result_view'),
    
    # Управление статусами инструментальных исследований
    path('instrumental/<int:pk>/status/complete/', 
         views.ExaminationInstrumentalCompleteView.as_view(), 
         name='instrumental_complete'),
    
    path('instrumental/<int:pk>/status/reject/', 
         views.ExaminationInstrumentalRejectView.as_view(), 
         name='instrumental_reject'),
    
    path('instrumental/<int:pk>/status/pause/', 
         views.ExaminationInstrumentalPauseView.as_view(), 
         name='instrumental_pause'),
    
    path('instrumental/<int:pk>/edit/', 
         views.ExaminationInstrumentalUpdateView.as_view(), 
         name='instrumental_update'),
    
    path('instrumental/<int:pk>/cancel/', 
         views.ExaminationInstrumentalCancelView.as_view(), 
         name='instrumental_cancel'),
    
    path('instrumental/<int:pk>/delete/', 
         views.ExaminationInstrumentalDeleteView.as_view(), 
         name='instrumental_delete'),
] 