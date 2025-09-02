from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied

from .models import Patient, PatientContact, PatientAddress, PatientDocument
from newborns.models import NewbornProfile


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'birth_date', 'gender', 'patient_type', 'age_display', 'archive_status', 'archive_actions')
    list_filter = ('patient_type', 'gender', 'birth_date', 'is_archived')
    search_fields = ('last_name', 'first_name', 'middle_name')
    date_hierarchy = 'birth_date'
    actions = ['archive_selected', 'restore_selected']
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('last_name', 'first_name', 'middle_name', 'birth_date', 'gender', 'patient_type')
        }),
        (_('Архивирование'), {
            'fields': ('is_archived', 'archived_at', 'archived_by', 'archive_reason'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('archived_at', 'archived_by')
    
    def get_queryset(self, request):
        # Получаем базовый queryset без применения фильтров Django Admin
        qs = self.model.objects.all()
        
        # Проверяем, есть ли фильтр по архивированию в параметрах запроса
        if 'is_archived__exact' in request.GET:
            # Если фильтр указан, применяем его
            is_archived_value = request.GET.get('is_archived__exact')
            if is_archived_value == '1':
                return qs.filter(is_archived=True)
            elif is_archived_value == '0':
                return qs.filter(is_archived=False)
        elif 'is_archived' in request.GET:
            # Если есть другие параметры архивирования, применяем их
            is_archived_value = request.GET.get('is_archived')
            if is_archived_value == '1':
                return qs.filter(is_archived=True)
            elif is_archived_value == '0':
                return qs.filter(is_archived=False)
        else:
            # По умолчанию показываем только активных пациентов
            return qs.filter(is_archived=False)

    def full_name(self, obj):
        return obj.get_full_name_with_age()
    full_name.short_description = _('ФИО и возраст')
    
    def age_display(self, obj):
        age = obj.get_age()
        if age is not None:
            return f"{age} лет"
        return "Не указан"
    age_display.short_description = _('Возраст')
    
    def archive_status(self, obj):
        if obj.is_archived:
            return format_html('<span style="color: orange;">📦 Архивирован</span>')
        else:
            return format_html('<span style="color: green;">✅ Активен</span>')
    archive_status.short_description = _('Статус')
    
    def archive_actions(self, obj):
        if obj.is_archived:
            return format_html(
                '<a class="button" href="{}">Восстановить</a>',
                f'/admin/patients/patient/{obj.pk}/restore/'
            )
        else:
            return format_html(
                '<a class="button" href="{}">Архивировать</a>',
                f'/admin/patients/patient/{obj.pk}/archive/'
            )
    archive_actions.short_description = _('Действия')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:patient_id>/archive/',
                self.admin_site.admin_view(self.archive_patient),
                name='patient-archive',
            ),
            path(
                '<int:patient_id>/restore/',
                self.admin_site.admin_view(self.restore_patient),
                name='patient-restore',
            ),
        ]
        return custom_urls + urls

    def archive_patient(self, request, patient_id):
        """Архивирует пациента"""
        try:
            patient = Patient.objects.get(pk=patient_id)
            if patient.is_archived:
                messages.warning(request, f"Пациент {patient} уже архивирован")
            else:
                # Используем универсальную систему архивирования
                from base.services import ArchiveService
                success = ArchiveService.archive_record(
                    instance=patient,
                    user=request.user,
                    reason="Архивирование через Django Admin",
                    request=request,
                    cascade=True
                )
                if success:
                    messages.success(request, f"Пациент {patient} успешно архивирован")
                else:
                    messages.error(request, f"Не удалось архивировать пациента {patient}")
        except Patient.DoesNotExist:
            messages.error(request, "Пациент не найден")
        except Exception as e:
            messages.error(request, f"Ошибка при архивировании: {str(e)}")
        
        return HttpResponseRedirect("../")

    def restore_patient(self, request, patient_id):
        """Восстанавливает пациента"""
        try:
            patient = Patient.objects.get(pk=patient_id)
            if not patient.is_archived:
                messages.warning(request, f"Пациент {patient} не архивирован")
            else:
                # Используем универсальную систему восстановления
                from base.services import ArchiveService
                success = ArchiveService.restore_record(
                    instance=patient,
                    user=request.user,
                    request=request,
                    cascade=True
                )
                if success:
                    messages.success(request, f"Пациент {patient} успешно восстановлен")
                else:
                    messages.error(request, f"Не удалось восстановить пациента {patient}")
        except Patient.DoesNotExist:
            messages.error(request, "Пациент не найден")
        except Exception as e:
            messages.error(request, f"Ошибка при восстановлении: {str(e)}")
        
        return HttpResponseRedirect("../")

    def archive_selected(self, request, queryset):
        """Архивирует выбранных пациентов"""
        archived_count = 0
        for patient in queryset:
            if not patient.is_archived:
                try:
                    # Используем универсальную систему архивирования
                    from base.services import ArchiveService
                    success = ArchiveService.archive_record(
                        instance=patient,
                        user=request.user,
                        reason="Массовое архивирование через Django Admin",
                        request=request,
                        cascade=True
                    )
                    if success:
                        archived_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при архивировании {patient}: {str(e)}")
        
        if archived_count > 0:
            messages.success(request, f"Успешно архивировано {archived_count} пациентов")
        else:
            messages.warning(request, "Нет пациентов для архивирования")
    
    archive_selected.short_description = _("Архивировать выбранных пациентов")

    def restore_selected(self, request, queryset):
        """Восстанавливает выбранных пациентов"""
        restored_count = 0
        for patient in queryset:
            if patient.is_archived:
                try:
                    # Используем универсальную систему восстановления
                    from base.services import ArchiveService
                    success = ArchiveService.restore_record(
                        instance=patient,
                        user=request.user,
                        request=request,
                        cascade=True
                    )
                    if success:
                        restored_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при восстановлении {patient}: {str(e)}")
        
        if restored_count > 0:
            messages.success(request, f"Успешно восстановлено {restored_count} пациентов")
        else:
            messages.warning(request, "Нет пациентов для восстановления")
    
    restore_selected.short_description = _("Восстановить выбранных пациентов")


@admin.register(PatientContact)
class PatientContactAdmin(admin.ModelAdmin):
    list_display = ('patient', 'phone', 'email', 'legal_representative_full_name', 'archive_status')
    list_filter = ('is_archived',)
    search_fields = ('patient__last_name', 'patient__first_name', 'phone', 'email')
    readonly_fields = ('archived_at', 'archived_by')
    
    def get_queryset(self, request):
        # Получаем базовый queryset без применения фильтров Django Admin
        qs = self.model.objects.all()
        
        # Проверяем, есть ли фильтр по архивированию в параметрах запроса
        if 'is_archived__exact' in request.GET:
            # Если фильтр указан, применяем его
            is_archived_value = request.GET.get('is_archived__exact')
            if is_archived_value == '1':
                return qs.filter(is_archived=True)
            elif is_archived_value == '0':
                return qs.filter(is_archived=False)
        elif 'is_archived' in request.GET:
            # Если есть другие параметры архивирования, применяем их
            is_archived_value = request.GET.get('is_archived')
            if is_archived_value == '1':
                return qs.filter(is_archived=True)
            elif is_archived_value == '0':
                return qs.filter(is_archived=False)
        else:
            # По умолчанию показываем только активные контакты
            return qs.filter(is_archived=False)

    def archive_status(self, obj):
        if obj.is_archived:
            return format_html('<span style="color: orange;">📦 Архивирован</span>')
        else:
            return format_html('<span style="color: green;">✅ Активен</span>')
    archive_status.short_description = _('Статус')
