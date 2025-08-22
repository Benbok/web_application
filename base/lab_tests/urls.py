from django.urls import path
from .views import (
    LabTestResultListView,
    LabTestResultCreateView,
    LabTestResultDetailView,
    LabTestResultUpdateView,
    LabTestResultDeleteView
)

app_name = 'lab_tests'

urlpatterns = [
    path('results/', LabTestResultListView.as_view(), name='result_list'),
    path('results/create/', LabTestResultCreateView.as_view(), name='result_create'),
    path('results/<int:pk>/', LabTestResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', LabTestResultUpdateView.as_view(), name='result_update'),
    path('results/<int:pk>/delete/', LabTestResultDeleteView.as_view(), name='result_delete'),
]