from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.AppointmentListView.as_view(), name='calendar'),
    path('new/', views.AppointmentCreateView.as_view(), name='create'),
]