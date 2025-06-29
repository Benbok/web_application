from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    path('<int:pk>/', views.EncounterDetailView.as_view(), name='encounter_detail'),
    path('add/<int:patient_pk>/', views.EncounterCreateView.as_view(), name='encounter_create'),
    path('<int:pk>/edit/', views.EncounterUpdateView.as_view(), name='encounter_update'),
    path('<int:pk>/delete/', views.EncounterDeleteView.as_view(), name='encounter_delete'),
]
