from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model

from .models import Encounter, TreatmentLabTest
from .services.encounter_service import EncounterService
from .forms import EncounterReopenForm, EncounterUndoForm

User = get_user_model()

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'patient', 'date_start', 'is_active', 'is_archived', 'archived_at', 'outcome')
    list_filter = ('is_active', 'is_archived', 'date_start', 'outcome')
    search_fields = ('patient__last_name', 'patient__first_name', 'patient__middle_name')
    actions = ['archive_selected', 'unarchive_selected', 'reopen_selected']
    readonly_fields = ('command_history', 'last_command_info')

    def archive_selected(self, request, queryset):
        for obj in queryset:
            service = EncounterService(obj)
            service.archive_encounter(user=request.user)
        self.message_user(request, f"{queryset.count()} записей архивировано.")
    archive_selected.short_description = "Архивировать выбранные"

    def unarchive_selected(self, request, queryset):
        for obj in queryset:
            service = EncounterService(obj)
            service.unarchive_encounter(user=request.user)
        self.message_user(request, f"{queryset.count()} записей восстановлено из архива.")
    unarchive_selected.short_description = "Восстановить из архива"

    def reopen_selected(self, request, queryset):
        """Возвращает выбранные случаи в активное состояние"""
        count = 0
        for obj in queryset:
            if not obj.is_active:
                service = EncounterService(obj)
                if service.reopen_encounter(user=request.user):
                    count += 1
        
        if count > 0:
            self.message_user(request, f"{count} случаев возвращено в активное состояние.")
        else:
            self.message_user(request, "Нет случаев для возврата в активное состояние.", level=messages.WARNING)
    reopen_selected.short_description = "Возвратить в активное состояние"

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:encounter_id>/reopen/',
                self.admin_site.admin_view(self.reopen_encounter_view),
                name='encounter_reopen',
            ),
            path(
                '<int:encounter_id>/undo/',
                self.admin_site.admin_view(self.undo_operation_view),
                name='encounter_undo',
            ),
        ]
        return custom_urls + urls
    
    def reopen_encounter_view(self, request, encounter_id):
        """Представление для возврата случая в активное состояние"""
        encounter = get_object_or_404(Encounter, id=encounter_id)
        
        if request.method == 'POST':
            form = EncounterReopenForm(encounter, request.POST)
            if form.is_valid():
                try:
                    form.save(user=request.user)
                    messages.success(request, f"Случай {encounter} успешно возвращен в активное состояние.")
                    return HttpResponseRedirect('../')
                except Exception as e:
                    messages.error(request, f"Ошибка при возврате случая: {e}")
        else:
            form = EncounterReopenForm(encounter)
        
        context = {
            'title': f'Возврат случая {encounter} в активное состояние',
            'form': form,
            'encounter': encounter,
        }
        return render(request, 'admin/encounters/encounter/reopen_form.html', context)
    
    def undo_operation_view(self, request, encounter_id):
        """Представление для отмены последней операции"""
        encounter = get_object_or_404(Encounter, id=encounter_id)
        
        if request.method == 'POST':
            form = EncounterUndoForm(encounter, request.POST)
            if form.is_valid():
                try:
                    form.save(user=request.user)
                    messages.success(request, f"Последняя операция для случая {encounter} успешно отменена.")
                    return HttpResponseRedirect('../')
                except Exception as e:
                    messages.error(request, f"Ошибка при отмене операции: {e}")
        else:
            form = EncounterUndoForm(encounter)
        
        context = {
            'title': f'Отмена последней операции для случая {encounter}',
            'form': form,
            'encounter': encounter,
        }
        return render(request, 'admin/encounters/encounter/undo_form.html', context)
    
    def command_history(self, obj):
        """Отображает историю команд"""
        service = EncounterService(obj)
        history = service.get_command_history()
        
        if not history:
            return "История команд пуста"
        
        history_text = []
        for i, command in enumerate(history[-5:], 1):  # Показываем последние 5 команд
            status = "✅" if command['execution_successful'] else "❌"
            history_text.append(f"{i}. {status} {command['description']}")
        
        return "<br>".join(history_text)
    command_history.short_description = "История команд"
    command_history.allow_tags = True
    
    def last_command_info(self, obj):
        """Отображает информацию о последней команде"""
        service = EncounterService(obj)
        last_command = service.get_last_command()
        
        if not last_command:
            return "Нет выполненных команд"
        
        status = "✅" if last_command['execution_successful'] else "❌"
        can_undo = "🔄" if last_command['can_undo'] else "❌"
        
        return f"{status} {last_command['description']} {can_undo}"
    last_command_info.short_description = "Последняя команда"
    last_command_info.allow_tags = True


@admin.register(TreatmentLabTest)
class TreatmentLabTestAdmin(admin.ModelAdmin):
    list_display = ('get_lab_test_name', 'treatment_plan', 'priority', 'is_active', 'created_at')
    list_filter = ('priority', 'is_active', 'created_at')
    search_fields = ('lab_test__name', 'custom_lab_test', 'treatment_plan__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('treatment_plan', 'lab_test', 'custom_lab_test', 'priority')
        }),
        ('Дополнительно', {
            'fields': ('instructions', 'is_active')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_lab_test_name(self, obj):
        return obj.get_lab_test_name()
    get_lab_test_name.short_description = 'Название исследования'


