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
    title = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentEvent
        fields = ('id', 'schedule', 'patient', 'start', 'end', 'notes', 'status', 'title')

    def get_title(self, obj):
        patient_name = obj.patient.full_name if obj.patient else "Неизвестный пациент"
        doctor_name = obj.schedule.doctor.doctor_profile.full_name if obj.schedule and obj.schedule.doctor and hasattr(obj.schedule.doctor, 'doctor_profile') else "Неизвестный врач"
        return f"{patient_name} - {doctor_name}"