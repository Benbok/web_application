# appointments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppointmentEventViewSet,
    CalendarView,
    AppointmentCreateView,
    AppointmentUpdateView
)

router = DefaultRouter()
router.register(r'events', AppointmentEventViewSet, basename='appointmentevent')

app_name = 'appointments'

urlpatterns = [
    path('', include(router.urls)),
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('create/', AppointmentCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', AppointmentUpdateView.as_view(), name='edit'),
]
