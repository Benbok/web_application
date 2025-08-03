from django.urls import path
from . import views

app_name = 'pharmacy'

urlpatterns = [
    path('', views.MedicationListView.as_view(), name='medication_list'),
    path('api/medications/<int:pk>/', views.medication_detail_api, name='medication_detail_api'),
    path('api/ajax-search/', views.MedicationAjaxSearchView.as_view(), name='ajax_search'),
    path('api/ajax-search-light/', views.MedicationAjaxSearchLightView.as_view(), name='ajax_search_light'),
]