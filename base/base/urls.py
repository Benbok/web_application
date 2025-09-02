"""
URL configuration for base project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from appointments.views import AppointmentEventViewSet
from . import views

app_name = 'base'

urlpatterns = [
    # Основные URL-адреса приложений
    path('admin/', admin.site.urls),
    path('select2/', include('django_select2.urls')),  # Добавляем URL-адреса django-select2
    path('auth/', include('authentication.urls')),  # URL-адреса для аутентификации
    path('', include('patients.urls')),  # ← Вот это подключает страницу с Vue
    path('encounters/', include('encounters.urls')),
    path('documents/', include('documents.urls')),
    path('departments/', include('departments.urls')),
    # path('treatment_assignments/', include('treatment_assignments.urls')),  # УДАЛЕНО
    path('pharmacy/', include('pharmacy.urls')),
    path('instrumental_procedures/', include('instrumental_procedures.urls')),
    path('lab_tests/', include('lab_tests.urls')),
    path('appointments/', include('appointments.urls')),
    path('diagnosis/', include('diagnosis.urls')),  # Добавляем URL-адреса diagnosis
    path('treatment/', include('treatment_management.urls')),  # Добавляем URL-адреса treatment_management
    path('examination/', include('examination_management.urls')),  # Добавляем URL-адреса examination_management
    path('scheduling/', include('clinical_scheduling.urls')),  # Добавляем URL-адреса clinical_scheduling
    path('signatures/', include('document_signatures.urls')),  # URL-адреса document_signatures
    
    # Система архивирования - добавляем после основных приложений
    path('archive/<str:app_label>/<str:model_name>/<int:pk>/', 
         views.archive_record, name='archive_record'),
    path('restore/<str:app_label>/<str:model_name>/<int:pk>/', 
         views.restore_record, name='restore_record'),
    path('bulk-archive/<str:app_label>/<str:model_name>/', 
         views.bulk_archive, name='bulk_archive'),
    path('archive-list/<str:app_label>/<str:model_name>/', 
         views.archive_list, name='archive_list'),
    
    # Логи и конфигурация архивирования
    path('archive-logs/', views.archive_logs, name='archive_logs'),
    path('archive-configuration/', views.archive_configuration, name='archive_configuration'),
    
    # AJAX API для архивирования
    path('archive-ajax/', views.archive_ajax, name='archive_ajax'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
