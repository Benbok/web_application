from rest_framework import serializers
from .models import AppointmentEvent

class AppointmentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentEvent
        fields = (
            'id', 'doctor', 'patient', 'start', 'end', 'notes', 'status', 'recurrence'
        )


# appointments/views.py
from rest_framework import viewsets
from .models import AppointmentEvent
from .serializers import AppointmentEventSerializer

class AppointmentEventViewSet(viewsets.ModelViewSet):
    queryset = AppointmentEvent.objects.all()
    serializer_class = AppointmentEventSerializer