from django.urls import path
from . import views

app_name = 'diagnosis'

urlpatterns = [
    # AJAX endpoints для Select2
    path('ajax/search/', views.DiagnosisAjaxSearchView.as_view(), name='ajax_search'),
    path('ajax/search-light/', views.DiagnosisAjaxSearchLightView.as_view(), name='ajax_search_light'),
] 