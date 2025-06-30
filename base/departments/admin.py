from django.contrib import admin
from .models import Department, PatientDepartmentStatus

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'description')
    search_fields = ('name', 'number')
    list_filter = ('name',)
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': ('name', 'number', 'description')
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
    list_display = ('patient', 'department', 'status', 'admission_date')
    search_fields = ('patient__name', 'department__name', 'status')
    list_filter = ('status', 'department')
    ordering = ('-admission_date',)

    fieldsets = (
        (None, {
            'fields': ('patient', 'department', 'status')
        }),
    )

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
 
 