from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Patient
from newborns.models import NewbornProfile


class NewbornProfileInline(admin.StackedInline):
    model = NewbornProfile
    can_delete = False
    verbose_name_plural = 'Профиль новорожденного'
    fk_name = 'patient'
    # Оставляем только специфичные для новорожденного поля
    fields = (
        'gestational_age_weeks',
        'birth_weight_grams',
        'birth_height_cm',
        'head_circumference_cm',
        'apgar_score_1_min',
        'apgar_score_5_min',
        'notes',
    )
    # Скрываем поля, которые теперь берутся из основной модели Patient
    exclude = ('birth_datetime',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    inlines = (NewbornProfileInline,)

    list_display = (
        'full_name',  # Используем свойство для полного имени
        'birth_date',
        'gender',
        'patient_type'
    )
    search_fields = ('last_name', 'first_name', 'middle_name', 'phone')
    list_filter = ('patient_type', 'gender')
    readonly_fields = ('created_at', 'updated_at', 'display_children')  # Добавляем новое поле

    # --- ИЗМЕНЕНИЕ 1: Улучшаем виджет для выбора родителей ---
    filter_horizontal = ('parents',)

    fieldsets = (
        ("Основная информация", {
            'fields': ('patient_type', ('last_name', 'first_name', 'middle_name'), ('birth_date', 'gender'))
        }),
        # --- ИЗМЕНЕНИЕ 2: Добавляем секции для отображения связей ---
        ("Семейные связи", {
            'fields': ('parents', 'display_children')  # Добавляем родителей и детей
        }),
        ("Контакты", {
            'fields': ('phone', 'email')
        }),
        ("Адреса", {
            'fields': ('registration_address', 'residential_address')
        }),
        ("Документы", {
            'fields': (
                'snils', 'insurance_policy_number', 'insurance_company',
                'passport_series', 'passport_number', 'passport_issued_by',
                'passport_issued_date', 'passport_department_code'
            ),
            'classes': ('collapse',)  # Делаем блок сворачиваемым
        }),
        ("Представитель", {
            'fields': (
                'legal_representative_full_name',
                'legal_representative_relation',
                'legal_representative_contacts'
            ),
            'classes': ('collapse',)  # Делаем блок сворачиваемым
        }),
        ("Служебная информация", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Этот метод - правильный способ сделать поле нередактируемым
        только на странице ИЗМЕНЕНИЯ существующего объекта.
        """
        # Если obj существует, значит, мы редактируем, а не создаем
        if obj:
            # Добавляем 'patient_type' к списку нередактируемых полей
            return self.readonly_fields + ('patient_type',)

        # Если мы создаем нового пациента, возвращаем базовый список
        return self.readonly_fields

    def get_inlines(self, request, obj=None):
        if obj and obj.patient_type == 'newborn':
            return (NewbornProfileInline,)
        return ()

    # --- ИЗМЕНЕНИЕ 3: Новый метод для отображения детей ---
    def display_children(self, obj):
        """Отображает список детей в виде кликабельных ссылок."""
        children = obj.children.all()
        if not children:
            return "Нет данных"
        links = []
        for child in children:
            url = reverse("admin:patients_patient_change", args=[child.pk])
            links.append(f'<a href="{url}">{child.full_name}</a>')
        return format_html('<br>'.join(links))

    display_children.short_description = "Дети"  # Название колонки/поля