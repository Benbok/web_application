from django.urls import path
from .views import (
    InstrumentalProcedureResultListView, 
    InstrumentalProcedureResultCreateView, 
    InstrumentalProcedureResultDetailView,
    InstrumentalProcedureResultUpdateView,
    InstrumentalProcedureResultSignView,
    InstrumentalProcedureRejectView
)

app_name = 'instrumental_procedures'

urlpatterns = [
    path('results/', InstrumentalProcedureResultListView.as_view(), name='result_list'),
    path('results/create/', InstrumentalProcedureResultCreateView.as_view(), name='result_create'),
    path('results/<int:pk>/', InstrumentalProcedureResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', InstrumentalProcedureResultUpdateView.as_view(), name='result_update'),
    path('results/<int:pk>/sign/', 
         InstrumentalProcedureResultSignView.as_view(), 
         name='result_sign'),
    path('results/<int:pk>/reject/', 
         InstrumentalProcedureRejectView.as_view(), 
         name='result_reject'),
]