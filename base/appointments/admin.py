# appointments/admin.py

from django.contrib import admin
from .models import Appointment, Schedule

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    # Заменяем старые имена полей на новые
    list_display = ('id', 'patient', 'doctor', 'start_datetime', 'end_datetime', 'status')
    list_filter = ('status', 'start_datetime', 'doctor') # Здесь тоже исправляем
    search_fields = ('doctor__last_name', 'patient__last_name', 'notes')
    date_hierarchy = 'start_datetime' # И здесь
    list_editable = ('status',)
    autocomplete_fields = ['patient', 'doctor']

# Регистрируем новую модель Schedule для управления графиками
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'get_day_of_week_display', 'start_time', 'end_time')
    list_filter = ('doctor', 'day_of_week')
    search_fields = ('doctor__last_name',)