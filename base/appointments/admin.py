# appointments/admin.py
from django.contrib import admin
from .models import Schedule, AppointmentEvent

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """
    Админ-панель для модели Расписания (Schedule).
    """
    list_display = (
        'id',
        'doctor',
        'start_time',
        'end_time',
        'duration',
        'recurrences'  # Показываем правило повторения
    )
    list_filter = ('doctor',)
    search_fields = ('doctor__last_name', 'doctor__first_name')
    list_per_page = 20

@admin.register(AppointmentEvent)
class AppointmentEventAdmin(admin.ModelAdmin):
    """
    Админ-панель для модели Записи на прием (AppointmentEvent).
    """
    list_display = (
        'id',
        'patient',
        'doctor', # Используем наше @property свойство из модели
        'start',
        'end',
        'status',
    )
    list_filter = ('status', 'schedule__doctor') # Фильтруем по врачу через расписание
    search_fields = ('patient__full_name', 'schedule__doctor__last_name')
    list_editable = ('status',) # Позволяем менять статус прямо из списка
    autocomplete_fields = ('patient', 'schedule') # Удобный поиск с автодополнением
    date_hierarchy = 'start' # Быстрая навигация по датам
    list_per_page = 20