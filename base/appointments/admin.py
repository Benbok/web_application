from django.contrib import admin
from .models import Schedule, AppointmentEvent
from .forms import ScheduleAdminForm

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    form = ScheduleAdminForm
    list_display = ('id', 'doctor_full_name', 'start_time', 'end_time', 'duration', 'recurrences')
    list_filter = ('doctor',)
    search_fields = ('doctor__last_name', 'doctor__first_name')
    list_per_page = 20

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('doctor', 'doctor__doctor_profile')

    @admin.display(description='Врач')
    def doctor_full_name(self, obj):
        return obj.doctor.doctor_profile.full_name if obj.doctor and hasattr(obj.doctor, 'doctor_profile') else '—'

@admin.register(AppointmentEvent)
class AppointmentEventAdmin(admin.ModelAdmin):
    """Админ-панель для модели Записи на прием (AppointmentEvent)."""
    list_display = ('id', 'patient', 'doctor_full_name', 'start', 'end', 'status')
    list_filter = ('status', 'schedule__doctor')
    search_fields = ('patient__full_name', 'schedule__doctor__last_name')
    list_editable = ('status',)
    autocomplete_fields = ('patient', 'schedule')
    date_hierarchy = 'start'
    list_per_page = 20

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('patient', 'schedule__doctor', 'schedule__doctor__doctor_profile')

    @admin.display(description='Врач')
    def doctor_full_name(self, obj):
        if obj.doctor and hasattr(obj.doctor, 'doctor_profile') and obj.doctor.doctor_profile:
            return obj.doctor.doctor_profile.full_name
        return '—'
