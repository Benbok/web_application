from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'start_time', 'end_time')
    list_filter = ('doctor', 'start_time')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__user__username')