from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import DoctorProfile, TemporaryPosition

class TemporaryPositionInline(admin.TabularInline):
    model = TemporaryPosition
    extra = 1

class DoctorProfileInline(admin.StackedInline):
    model = DoctorProfile
    can_delete = False
    verbose_name_plural = 'Профиль врача'
    inlines = [TemporaryPositionInline] # Добавляем TemporaryPositionInline сюда

class UserAdmin(BaseUserAdmin):
    inlines = (DoctorProfileInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(TemporaryPosition)