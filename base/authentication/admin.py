from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Дополнительный профиль'
    fields = ('employee_id', 'department', 'position', 'phone', 'is_active_employee')
    extra = 0

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_doctor_name', 'get_doctor_position', 'get_department')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'userprofile__department', 'userprofile__is_active_employee')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'userprofile__employee_id', 'doctor_profile__full_name')
    
    def get_doctor_name(self, obj):
        if hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.full_name
        return '-'
    get_doctor_name.short_description = 'ФИО врача'
    
    def get_doctor_position(self, obj):
        if hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.get_current_position()
        return '-'
    get_doctor_position.short_description = 'Должность врача'
    
    def get_department(self, obj):
        if hasattr(obj, 'userprofile') and obj.userprofile.department:
            return obj.userprofile.department.name
        return '-'
    get_department.short_description = 'Отделение'

# Перерегистрируем UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'position', 'department', 'phone', 'is_active_employee', 'get_doctor_info')
    list_filter = ('department', 'is_active_employee', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id', 'position')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_doctor_info(self, obj):
        if hasattr(obj.user, 'doctor_profile'):
            return f"{obj.user.doctor_profile.full_name} ({obj.user.doctor_profile.specialization})"
        return 'Нет профиля врача'
    get_doctor_info.short_description = 'Информация о враче'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'employee_id', 'position', 'department')
        }),
        ('Контактная информация', {
            'fields': ('phone',)
        }),
        ('Статус', {
            'fields': ('is_active_employee',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
