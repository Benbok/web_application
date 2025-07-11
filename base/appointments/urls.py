# appointments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppointmentEventViewSet,
    CalendarView,
    AppointmentCreateView,
    AppointmentUpdateView,
    AvailableSlotsAPIView,
    AppointmentEventDetailView,
    AppointmentEventUpdateView,
    AppointmentEventDeleteView,
    save_session_params,
    CreateEncounterForAppointmentView
)

router = DefaultRouter()
router.register(r'events', AppointmentEventViewSet, basename='appointmentevent')

app_name = 'appointments'

urlpatterns = [
    path('', include(router.urls)),
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('create/', AppointmentCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', AppointmentUpdateView.as_view(), name='edit'),
    path('api/available-slots/', AvailableSlotsAPIView.as_view(), name='available_slots_api'),
    path('save-session-params/', save_session_params, name='save_session_params'),
    path('appointments/<int:pk>/', AppointmentEventDetailView.as_view(), name='detail'),
    path('appointments/<int:pk>/edit/', AppointmentEventUpdateView.as_view(), name='edit'),
    path('appointments/<int:pk>/delete/', AppointmentEventDeleteView.as_view(), name='delete'),
    path('appointment/<int:pk>/create-encounter/', CreateEncounterForAppointmentView.as_view(), name='create_encounter_for_appointment'),
]


