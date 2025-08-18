from django.urls import path
from .views import (
    LabTestAssignmentListView,
    LabTestResultCreateView,
    LabTestResultDetailView,
    LabTestResultUpdateView,
    LabTestAssignmentRejectView,
    LabTestResultDeleteView
)

app_name = 'lab_tests'

urlpatterns = [
    path('assignments/', LabTestAssignmentListView.as_view(), name='assignment_list'),
    path('assignments/<int:pk>/add_result/', LabTestResultCreateView.as_view(), name='add_result'),
    path('assignments/<int:pk>/reject/', LabTestAssignmentRejectView.as_view(), name='assignment_reject'),
    path('results/<int:pk>/', LabTestResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', LabTestResultUpdateView.as_view(), name='result_update'),
    path('results/<int:pk>/delete/', LabTestResultDeleteView.as_view(), name='result_delete'),
]