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
    
 
 