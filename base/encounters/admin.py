from django.contrib import admin
from .models import Encounter

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'patient', 'date_start', 'is_active', 'is_archived', 'archived_at')
    list_filter = ('is_active', 'is_archived', 'date_start')
    search_fields = ('patient__last_name', 'patient__first_name', 'patient__middle_name')
    actions = ['archive_selected', 'unarchive_selected']

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