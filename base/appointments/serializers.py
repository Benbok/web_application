# appointments/serializers.py

from rest_framework import serializers
from .models import AppointmentEvent, Schedule # Make sure Schedule is imported
from patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name')

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ('id', 'full_name')

class ScheduleSerializer(serializers.ModelSerializer):
    doctor = DoctorSerializer(read_only=True)
    class Meta:
        model = Schedule
        fields = '__all__'

class AppointmentEventSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    schedule = ScheduleSerializer(read_only=True)

    class Meta:
        model = AppointmentEvent

        fields = ('id', 'schedule', 'patient', 'start', 'end', 'notes', 'status')