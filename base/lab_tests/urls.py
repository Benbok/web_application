from django.urls import path
from .views import (
    LabTestResultListView,
    LabTestResultCreateView,
    LabTestResultDetailView,
    LabTestResultUpdateView,
    LabTestResultDeleteView,
    LabTestResultSignView,
    LabTestRejectView,
    LabTestDisqualifyView
)

app_name = 'lab_tests'

urlpatterns = [
    path('results/', LabTestResultListView.as_view(), name='result_list'),
    path('results/create/', LabTestResultCreateView.as_view(), name='result_create'),
    path('results/<int:pk>/', LabTestResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', LabTestResultUpdateView.as_view(), name='result_update'),
    path('results/<int:pk>/delete/', LabTestResultDeleteView.as_view(), name='result_delete'),
    path('results/<int:pk>/sign/', 
         LabTestResultSignView.as_view(), 
         name='result_sign'),
    path('results/<int:pk>/reject/', 
         LabTestRejectView.as_view(), 
         name='result_reject'),
    path('results/<int:pk>/disqualify/', 
         LabTestDisqualifyView.as_view(), 
         name='result_disqualify'),
]