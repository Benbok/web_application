from django.urls import path
from . import views

app_name = 'pharmacy'

urlpatterns = [
    path('', views.MedicationListView.as_view(), name='medication_list'),
    path('api/medications/<int:pk>/', views.medication_detail_api, name='medication_detail_api'),
]