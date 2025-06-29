from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    path('<int:pk>/', views.encounter_detail, name='encounter_detail'),
    path('add/<int:pk>/', views.encounter_create, name='encounter_create'),
    path('<int:pk>/edit/', views.encounter_update, name='encounter_update'),
    path('<int:pk>/delete/', views.encounter_delete, name='encounter_delete'),
]
