from django.contrib import admin
from .models import Department, PatientDepartmentStatus

from .models import Department
from .forms import DepartmentForm

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    form = DepartmentForm
    list_display = ('name', 'slug', 'description')
    search_fields = ('name', 'slug')
    list_filter = ('name',)
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
    )

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
@admin.register(PatientDepartmentStatus)
class PatientDepartmentStatusAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'patient', 'department', 'admission_date', 'status', 'is_archived', 'archived_at')
    list_filter = ('status', 'is_archived', 'admission_date')
    search_fields = ('patient__last_name', 'patient__first_name', 'patient__middle_name', 'department__name')
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
    
 
 