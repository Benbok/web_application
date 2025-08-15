from django.urls import path
from . import views

app_name = 'treatment_management'

urlpatterns = [
    # Планы лечения
    path('<str:owner_model>/<int:owner_id>/plans/', 
         views.TreatmentPlanListView.as_view(), 
         name='plan_list'),
    
    path('<str:owner_model>/<int:owner_id>/plans/create/', 
         views.TreatmentPlanCreateView.as_view(), 
         name='plan_create'),
    
    path('<str:owner_model>/<int:owner_id>/plans/<int:pk>/', 
         views.TreatmentPlanDetailView.as_view(), 
         name='plan_detail'),
    
    path('<str:owner_model>/<int:owner_id>/plans/<int:pk>/edit/', 
         views.TreatmentPlanUpdateView.as_view(), 
         name='plan_update'),
    
    path('<str:owner_model>/<int:owner_id>/plans/<int:pk>/delete/', 
         views.TreatmentPlanDeleteView.as_view(), 
         name='plan_delete'),
    
    # Лекарства в планах лечения
    path('plans/<int:plan_pk>/medications/add/', 
         views.TreatmentMedicationCreateView.as_view(), 
         name='medication_create'),
    
    path('medications/<int:pk>/edit/', 
         views.TreatmentMedicationUpdateView.as_view(), 
         name='medication_update'),
    
    path('medications/<int:pk>/delete/', 
         views.TreatmentMedicationDeleteView.as_view(), 
         name='medication_delete'),
    
    # Быстрое добавление лекарств
    path('plans/<int:plan_pk>/quick-add/', 
         views.QuickAddMedicationView.as_view(), 
         name='quick_add_medication'),
    
    path('plans/<int:plan_pk>/quick-add/<str:medication_name>/', 
         views.QuickAddMedicationView.as_view(), 
         name='quick_add_medication_by_name'),
    
    # Рекомендации в планах лечения
    path('plans/<int:plan_pk>/recommendations/add/', 
         views.TreatmentRecommendationCreateView.as_view(), 
         name='recommendation_create'),
    
    path('recommendations/<int:pk>/edit/', 
         views.TreatmentRecommendationUpdateView.as_view(), 
         name='recommendation_update'),
    
    path('recommendations/<int:pk>/delete/', 
         views.TreatmentRecommendationDeleteView.as_view(), 
         name='recommendation_delete'),
    
    # AJAX endpoints
    path('api/medication-info/<int:medication_id>/', 
         views.MedicationInfoView.as_view(), 
         name='medication_info'),
    
    path('api/trade-name-info/<int:trade_name_id>/', 
         views.TradeNameInfoView.as_view(), 
         name='trade_name_info'),
] 