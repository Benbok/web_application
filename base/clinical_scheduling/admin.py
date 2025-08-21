from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ScheduledAppointment

@admin.register(ScheduledAppointment)
class ScheduledAppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient', 'assignment_type', 'assignment_info', 'scheduled_date', 'scheduled_time', 
        'execution_status', 'created_department', 'is_overdue_display'
    ]
    
    list_filter = [
        'execution_status', 'scheduled_date', 'created_department', 'patient',
        ('encounter', admin.RelatedOnlyFieldListFilter),
        'created_at'
    ]
    
    search_fields = [
        'patient__last_name', 'patient__first_name', 'patient__middle_name',
        'patient__medical_record_number', 'execution_notes', 'rejection_reason'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'assignment_info', 'is_overdue_display',
        'can_be_executed_display', 'can_be_rejected_display'
    ]
    
    exclude = ['content_type', 'object_id']  # Исключаем поля GenericForeignKey
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('patient', 'assignment_info', 'scheduled_date', 'scheduled_time')
        }),
        (_('Контекст создания'), {
            'fields': ('created_department', 'encounter'),
            'classes': ('collapse',)
        }),
        (_('Статус выполнения'), {
            'fields': ('execution_status', 'executed_at', 'executed_by', 'execution_notes')
        }),
        (_('Отклонение'), {
            'fields': ('rejection_reason', 'rejection_date', 'rejected_by'),
            'classes': ('collapse',)
        }),
        (_('Частичное выполнение'), {
            'fields': ('partial_reason', 'partial_amount'),
            'classes': ('collapse',)
        }),
        (_('Метаданные'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def assignment_info(self, obj):
        """Отображает информацию о связанном назначении"""
        try:
            info = obj.get_assignment_info()
            if info['type'] == 'treatment':
                return format_html(
                    '<span class="badge bg-primary">{}</span> {}',
                    'Лечение', info['name']
                )
            elif info['type'] == 'lab_test':
                return format_html(
                    '<span class="badge bg-info">{}</span> {}',
                    'Лаборатория', info['name']
                )
            elif info['type'] == 'procedure':
                return format_html(
                    '<span class="badge bg-warning">{}</span> {}',
                    'Процедура', info['name']
                )
            else:
                return format_html(
                    '<span class="badge bg-secondary">{}</span>',
                    str(obj.assignment)
                )
        except Exception:
            return str(obj.assignment)
    
    assignment_info.short_description = _('Назначение')
    assignment_info.admin_order_field = 'content_type'
    
    def assignment_type(self, obj):
        """Отображает тип назначения"""
        try:
            info = obj.get_assignment_info()
            if info['type'] == 'treatment':
                return format_html('<span class="badge bg-primary">Лечение</span>')
            elif info['type'] == 'lab_test':
                return format_html('<span class="badge bg-info">Лаборатория</span>')
            elif info['type'] == 'procedure':
                return format_html('<span class="badge bg-warning">Процедура</span>')
            else:
                return format_html('<span class="badge bg-secondary">Неизвестно</span>')
        except Exception:
            return format_html('<span class="badge bg-secondary">Ошибка</span>')
    
    assignment_type.short_description = _('Тип')
    assignment_type.admin_order_field = 'content_type'
    
    def is_overdue_display(self, obj):
        """Отображает статус просроченности"""
        if obj.is_overdue:
            return format_html(
                '<span class="badge bg-danger">Просрочено</span>'
            )
        elif obj.is_due_today:
            return format_html(
                '<span class="badge bg-warning">Сегодня</span>'
            )
        else:
            return format_html(
                '<span class="badge bg-success">В будущем</span>'
            )
    
    is_overdue_display.short_description = _('Статус')
    is_overdue_display.admin_order_field = 'scheduled_date'
    
    def can_be_executed_display(self, obj):
        """Отображает возможность выполнения"""
        if obj.can_be_executed:
            return format_html(
                '<span class="badge bg-success">Можно выполнить</span>'
            )
        else:
            return format_html(
                '<span class="badge bg-secondary">Нельзя выполнить</span>'
            )
    
    can_be_executed_display.short_description = _('Возможность выполнения')
    
    def can_be_rejected_display(self, obj):
        """Отображает возможность отклонения"""
        if obj.can_be_rejected:
            return format_html(
                '<span class="badge bg-warning">Можно отклонить</span>'
            )
        else:
            return format_html(
                '<span class="badge bg-secondary">Нельзя отклонить</span>'
            )
    
    can_be_rejected_display.short_description = _('Возможность отклонения')
    
    def get_queryset(self, request):
        """Оптимизирует запросы"""
        return super().get_queryset(request).select_related(
            'patient', 'created_department', 'encounter', 
            'executed_by', 'rejected_by'
        )
    
    def has_add_permission(self, request):
        """Разрешаем создание только администраторам"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Проверяем права на редактирование"""
        if request.user.is_superuser:
            return True
        
        if obj is None:
            return True
        
        return obj.can_be_edited_by_user(request.user)
    
    def has_delete_permission(self, request, obj=None):
        """Проверяем права на удаление"""
        if request.user.is_superuser:
            return True
        
        if obj is None:
            return True
        
        return obj.can_be_edited_by_user(request.user)
