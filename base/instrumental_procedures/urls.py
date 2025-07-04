from django.urls import path
from .views import (
    InstrumentalProcedureAssignmentListView, 
    InstrumentalProcedureResultCreateView, 
    InstrumentalProcedureResultDetailView,
    InstrumentalProcedureResultUpdateView,
    InstrumentalProcedureResultDeleteView
)

app_name = 'instrumental_procedures'

urlpatterns = [
    path('assignments/', InstrumentalProcedureAssignmentListView.as_view(), name='assignment_list'),
    path('assignments/<int:pk>/add_result/', InstrumentalProcedureResultCreateView.as_view(), name='add_result'),
    path('results/<int:pk>/', InstrumentalProcedureResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', InstrumentalProcedureResultUpdateView.as_view(), name='result_update'),
    path('results/<int:pk>/delete/', InstrumentalProcedureResultDeleteView.as_view(), name='result_delete'),
]