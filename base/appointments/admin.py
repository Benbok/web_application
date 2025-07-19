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
    
    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение для корректной обработки времени"""
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('doctor', 'doctor__doctor_profile')

    @admin.display(description='Врач')
    def doctor_full_name(self, obj):
        return obj.doctor.doctor_profile.full_name if obj.doctor and hasattr(obj.doctor, 'doctor_profile') else '—'

@admin.register(AppointmentEvent)
class AppointmentEventAdmin(admin.ModelAdmin):
    """Админ-панель для модели Записи на прием (AppointmentEvent)."""
    list_display = ('__str__', 'patient', 'start', 'end', 'status', 'is_archived', 'archived_at')
    list_filter = ('status', 'is_archived', 'start')
    search_fields = ('patient__last_name', 'patient__first_name', 'patient__middle_name')
    actions = ['archive_selected', 'unarchive_selected']
    
    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение для корректной обработки времени"""
        from django.utils import timezone
        if obj.start and timezone.is_naive(obj.start):
            obj.start = timezone.make_aware(obj.start, timezone.get_current_timezone())
        if obj.end and timezone.is_naive(obj.end):
            obj.end = timezone.make_aware(obj.end, timezone.get_current_timezone())
        super().save_model(request, obj, form, change)

    def archive_selected(self, request, queryset):
        for obj in queryset:
            obj.archive()
        self.message_user(request, f"{queryset.count()} записей архивировано.")
    archive_selected.short_description = "Архивировать выбранные"

    def unarchive_selected(self, request, queryset):
        for obj in queryset:
            obj.is_archived = False
            obj.archived_at = None
            obj.save(update_fields=['is_archived', 'archived_at'])
        self.message_user(request, f"{queryset.count()} записей восстановлено из архива.")
    unarchive_selected.short_description = "Восстановить из архива"

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()

    @admin.display(description='Врач')
    def doctor_full_name(self, obj):
        if obj.doctor and hasattr(obj.doctor, 'doctor_profile') and obj.doctor.doctor_profile:
            return obj.doctor.doctor_profile.full_name
        return '—'
