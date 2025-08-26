from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import MedicalLoginView, MedicalLogoutView

app_name = 'authentication'

urlpatterns = [
    path('login/', MedicalLoginView.as_view(), name='login'),
    path('logout/', MedicalLogoutView.as_view(), name='logout'),
]
