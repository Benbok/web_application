# departments/urls.py (будет создан/дополнен)
from django.urls import path
from . import views

app_name = 'departments'

urlpatterns = [
    path('', views.DepartmentListView.as_view(), name='department_list'),
    path('<int:pk>/', views.DepartmentDetailView.as_view(), name='department_detail'),
    path('<int:department_pk>/patient_status/<int:pk>/accept/', views.PatientDepartmentAcceptView.as_view(), name='patient_status_accept'),
    path('<int:department_pk>/patient_status/<int:pk>/discharge/', views.PatientDepartmentDischargeView.as_view(), name='patient_status_discharge'),
    path('patient_status/<int:pk>/history/', views.PatientDepartmentHistoryView.as_view(), name='patient_history'),
]