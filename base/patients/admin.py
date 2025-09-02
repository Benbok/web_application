from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from .models import Patient, PatientContact, PatientAddress, PatientDocument
from newborns.models import NewbornProfile


class PatientContactInline(admin.StackedInline):
    model = PatientContact
    extra = 0


class PatientAddressInline(admin.StackedInline):
    model = PatientAddress
    extra = 0


class PatientDocumentInline(admin.StackedInline):
    model = PatientDocument
    extra = 0


class NewbornProfileInline(admin.StackedInline):
    model = NewbornProfile
    extra = 0
    verbose_name = "Профиль новорожденного"
    verbose_name_plural = "Профиль новорожденного"
    
    def get_queryset(self, request):
        # Показываем только для пациентов типа 'newborn'
        qs = super().get_queryset(request)
        return qs.filter(patient__patient_type='newborn')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'birth_date', 'gender', 'patient_type', 'age_display', 'archive_status', 'archive_actions')
    list_filter = ('patient_type', 'gender', 'birth_date', 'is_archived')
    search_fields = ('last_name', 'first_name', 'middle_name')
    date_hierarchy = 'birth_date'
    actions = ['archive_selected', 'restore_selected']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('patient_type', 'last_name', 'first_name', 'middle_name', 'birth_date', 'gender')
        }),
        ('Связи', {
            'fields': ('parents',),
            'classes': ('collapse',)
        }),
        ('Архивирование', {
            'fields': ('is_archived', 'archived_at', 'archived_by', 'archive_reason'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('archived_at', 'archived_by')
    
    def get_inlines(self, request, obj=None):
        inlines = [PatientContactInline, PatientAddressInline, PatientDocumentInline]
        # Добавляем inline для новорожденных только если пациент новорожденный
        if obj and obj.patient_type == 'newborn':
            inlines.append(NewbornProfileInline)
        return inlines
    
    def age_display(self, obj):
        if obj.birth_date:
            from datetime import date
            today = date.today()
            age = today.year - obj.birth_date.year - ((today.month, today.day) < (obj.birth_date.month, obj.birth_date.day))
            if age == 0:
                months = (today.year - obj.birth_date.year) * 12 + today.month - obj.birth_date.month
                if months == 0:
                    days = (today - obj.birth_date).days
                    return f"{days} дней"
                return f"{months} мес."
            return f"{age} лет"
        return "-"
    age_display.short_description = "Возраст"
    
    def archive_status(self, obj):
        if obj.is_archived:
            return format_html(
                '<span style="color: orange; font-weight: bold;">📦 Архивирован</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">✅ Активен</span>'
        )
    archive_status.short_description = "Статус"
    
    def archive_actions(self, obj):
        if obj.is_archived:
            # Кнопка восстановления
            restore_url = reverse('admin:patients_patient_restore', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="background-color: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">🔄 Восстановить</a>',
                restore_url
            )
        else:
            # Кнопка архивирования
            archive_url = reverse('admin:patients_patient_archive', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="background-color: #ffc107; color: black; padding: 5px 10px; text-decoration: none; border-radius: 3px;">📦 Архивировать</a>',
                archive_url
            )
    archive_actions.short_description = "Действия"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:patient_id>/archive/',
                self.admin_site.admin_view(self.archive_patient),
                name='patients_patient_archive',
            ),
            path(
                '<int:patient_id>/restore/',
                self.admin_site.admin_view(self.restore_patient),
                name='patients_patient_restore',
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
                # Архивируем пациента напрямую (обход проблемы с ArchiveService)
                patient.archive(
                    user=request.user,
                    reason="Архивирование через Django Admin"
                )
                success = True
                if success:
                    messages.success(request, f"Пациент {patient} успешно архивирован")
                else:
                    messages.error(request, f"Не удалось архивировать пациента {patient}")
        except Patient.DoesNotExist:
            messages.error(request, "Пациент не найден")
        except Exception as e:
            messages.error(request, f"Ошибка при архивировании: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:patients_patient_changelist'))
    
    def restore_patient(self, request, patient_id):
        """Восстанавливает пациента"""
        try:
            patient = Patient.objects.get(pk=patient_id)
            if not patient.is_archived:
                messages.warning(request, f"Пациент {patient} не архивирован")
            else:
                # Восстанавливаем пациента напрямую
                patient.restore(user=request.user)
                success = True
                if success:
                    messages.success(request, f"Пациент {patient} успешно восстановлен")
                else:
                    messages.error(request, f"Не удалось восстановить пациента {patient}")
        except Patient.DoesNotExist:
            messages.error(request, "Пациент не найден")
        except Exception as e:
            messages.error(request, f"Ошибка при восстановлении: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:patients_patient_changelist'))
    
    def archive_selected(self, request, queryset):
        """Массовое архивирование выбранных пациентов"""
        archived_count = 0
        for patient in queryset:
            if not patient.is_archived:
                try:
                    # Архивируем пациента напрямую (обход проблемы с ArchiveService)
                    patient.archive(
                        user=request.user,
                        reason="Массовое архивирование через Django Admin"
                    )
                    archived_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при архивировании {patient}: {str(e)}")
        
        if archived_count > 0:
            messages.success(request, f"Успешно архивировано {archived_count} пациентов")
        else:
            messages.warning(request, "Не удалось архивировать ни одного пациента")
    
    archive_selected.short_description = "Архивировать выбранных пациентов"
    
    def restore_selected(self, request, queryset):
        """Массовое восстановление выбранных пациентов"""
        restored_count = 0
        for patient in queryset:
            if patient.is_archived:
                try:
                    # Восстанавливаем пациента напрямую
                    patient.restore(user=request.user)
                    restored_count += 1
                except Exception as e:
                    messages.error(request, f"Ошибка при восстановлении {patient}: {str(e)}")
        
        if restored_count > 0:
            messages.success(request, f"Успешно восстановлено {restored_count} пациентов")
        else:
            messages.warning(request, "Не удалось восстановить ни одного пациента")
    
    restore_selected.short_description = "Восстановить выбранных пациентов"
    
    def get_queryset(self, request):
        """Возвращает QuerySet с учетом фильтрации по архивированию"""
        qs = super().get_queryset(request)
        
        # Добавляем фильтр по архивированию, если не указан явно
        if 'is_archived' not in request.GET:
            # По умолчанию показываем только активных пациентов
            qs = qs.filter(is_archived=False)
        
        return qs


@admin.register(PatientContact)
class PatientContactAdmin(admin.ModelAdmin):
    list_display = ('patient', 'phone', 'email', 'legal_representative_full_name', 'archive_status')
    list_filter = ('is_archived',)
    search_fields = ('patient__last_name', 'patient__first_name', 'phone', 'email')
    readonly_fields = ('archived_at', 'archived_by')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('patient', 'phone', 'email')
        }),
        ('Законный представитель', {
            'fields': ('legal_representative_full_name', 'legal_representative_relation', 'legal_representative_contacts')
        }),
        ('Архивирование', {
            'fields': ('is_archived', 'archived_at', 'archived_by', 'archive_reason'),
            'classes': ('collapse',)
        }),
    )
    
    def archive_status(self, obj):
        if obj.is_archived:
            return format_html(
                '<span style="color: orange; font-weight: bold;">📦 Архивирован</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">✅ Активен</span>'
        )
    archive_status.short_description = "Статус"
    
    def get_queryset(self, request):
        """Возвращает QuerySet с учетом фильтрации по архивированию"""
        qs = super().get_queryset(request)
        
        # Добавляем фильтр по архивированию, если не указан явно
        if 'is_archived' not in request.GET:
            # По умолчанию показываем только активные контакты
            qs = qs.filter(is_archived=False)
        
        return qs
