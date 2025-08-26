from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patient/add/', views.patient_create, name='patient_create'),
    path('patient/<int:pk>/', views.patient_detail, name='patient_detail'),
    # urls.py
    path('patient/<int:parent_id>/newborn/', views.newborn_create, name='newborn_create'),
    path('patient/<int:parent_id>/child/', views.child_create, name='child_create'),
    path('patient/<int:parent_id>/teen/', views.teen_create, name='teen_create'),

    path('patient/<int:pk>/edit/', views.patient_update, name='patient_update'),
    path('patient/<int:pk>/delete/', views.patient_delete, name='patient_delete'),
]
