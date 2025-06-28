from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    path('', views.home, name='encounters'),
]
