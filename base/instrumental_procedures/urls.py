from django.urls import path
from .views import (
    InstrumentalProcedureResultListView, 
    InstrumentalProcedureResultCreateView, 
    InstrumentalProcedureResultDetailView,
    InstrumentalProcedureResultUpdateView
)

app_name = 'instrumental_procedures'

urlpatterns = [
    path('results/', InstrumentalProcedureResultListView.as_view(), name='result_list'),
    path('results/create/', InstrumentalProcedureResultCreateView.as_view(), name='result_create'),
    path('results/<int:pk>/', InstrumentalProcedureResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', InstrumentalProcedureResultUpdateView.as_view(), name='result_update'),
]