from django.urls import path
from .views import InstrumentalProcedureAssignmentListView, InstrumentalProcedureResultCreateView, InstrumentalProcedureResultDetailView

app_name = 'instrumental_procedures'

urlpatterns = [
    path('assignments/', InstrumentalProcedureAssignmentListView.as_view(), name='assignment_list'),
    path('assignments/<int:pk>/add_result/', InstrumentalProcedureResultCreateView.as_view(), name='add_result'),
    path('results/<int:pk>/', InstrumentalProcedureResultDetailView.as_view(), name='result_detail'),
]