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
urlpatterns = [
    path('admin/', admin.site.urls),
    path('select2/', include('django_select2.urls')), # Добавляем URL-адреса django-select2
    path('patients/', include('patients.urls')),  # ← Вот это подключает страницу с Vue
    path('encounters/', include('encounters.urls')),
    path('documents/', include('documents.urls')),
    path('departments/', include('departments.urls')),
    path('treatment_assignments/', include('treatment_assignments.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('instrumental_procedures/', include('instrumental_procedures.urls')),
    path('lab_tests/', include('lab_tests.urls')),
    path('appointments/', include('appointments.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
