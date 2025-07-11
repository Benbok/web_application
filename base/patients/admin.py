from django.contrib import admin
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
    list_display = ('full_name', 'birth_date', 'gender', 'patient_type', 'age_display')
    list_filter = ('patient_type', 'gender', 'birth_date')
    search_fields = ('last_name', 'first_name', 'middle_name')
    date_hierarchy = 'birth_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('patient_type', 'last_name', 'first_name', 'middle_name', 'birth_date', 'gender')
        }),
        ('Связи', {
            'fields': ('parents',),
            'classes': ('collapse',)
        }),
    )
    
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
