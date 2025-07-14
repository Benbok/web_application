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
    doctor_full_name = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentEvent
        fields = ('id', 'schedule', 'patient', 'start', 'end', 'notes', 'status', 'title', 'doctor_full_name')

    def get_title(self, obj):
        # ФИО пациента
        if obj.patient and obj.patient.full_name:
            parts = obj.patient.full_name.split()
            if len(parts) >= 2:
                fio_patient = f"{parts[0]} {parts[1][0]}."
                if len(parts) > 2:
                    fio_patient += f"{parts[2][0]}."
            else:
                fio_patient = obj.patient.full_name
        else:
            fio_patient = str(obj.patient)
        # ФИО врача
        fio_doctor = self.get_doctor_full_name(obj)
        if fio_doctor:
            return f"{fio_patient} —> врач:{fio_doctor}"
        return fio_patient

    def get_doctor_full_name(self, obj):
        if obj.schedule and obj.schedule.doctor:
            doctor = obj.schedule.doctor
            if hasattr(doctor, 'doctor_profile') and doctor.doctor_profile:
                return doctor.doctor_profile.full_name
            else:
                return f"{doctor.last_name} {doctor.first_name}"
        return None