from django.urls import path
from . import views

app_name = 'clinical_scheduling'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('schedule-settings/', views.schedule_settings, name='schedule_settings'),
    path('appointment/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointment/<int:appointment_id>/complete/', views.mark_as_completed, name='mark_completed'),
    path('appointment/<int:appointment_id>/reject/', views.mark_as_rejected, name='mark_rejected'),
    path('appointment/<int:appointment_id>/skip/', views.mark_as_skipped, name='mark_skipped'),
    path('appointment/<int:appointment_id>/partial/', views.mark_as_partial, name='mark_partial'),
    path('today/', views.today_schedule, name='today_schedule'),
    path('patient/<int:patient_id>/', views.patient_schedule, name='patient_schedule'),
]