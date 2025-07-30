from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MedicationGroup, ReleaseForm, AdministrationMethod, Medication, 
    TradeName, Regimen, PopulationCriteria, DosingInstruction, RegimenAdjustment
)


@admin.register(MedicationGroup)
class MedicationGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview')
    search_fields = ('name', 'description')
    list_per_page = 50

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return '—'
    description_preview.short_description = 'Описание'


@admin.register(ReleaseForm)
class ReleaseFormAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview')
    search_fields = ('name', 'description')
    list_per_page = 50

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return '—'
    description_preview.short_description = 'Описание'


@admin.register(AdministrationMethod)
class AdministrationMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview')
    search_fields = ('name', 'description')
    list_per_page = 50

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return '—'
    description_preview.short_description = 'Описание'


class TradeNameInline(admin.TabularInline):
    model = TradeName
    extra = 0
    fields = ('name', 'medication_group', 'atc_code', 'release_form', 'external_info_link')
    readonly_fields = ('external_info_link',)
    
    def external_info_link(self, obj):
        if obj.external_info_url:
            return format_html('<a href="{}" target="_blank">Ссылка</a>', obj.external_info_url)
        return '—'
    external_info_link.short_description = 'Внешняя информация'


# Убираем RegimenInline, так как у Regimen нет связи с TradeName


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_info_link', 'trade_names_count', 'trade_names_link')
    search_fields = ('name',)
    list_per_page = 50
    inlines = [TradeNameInline]

    def external_info_link(self, obj):
        if obj.external_info_url:
            return format_html('<a href="{}" target="_blank">Ссылка</a>', obj.external_info_url)
        return '—'
    external_info_link.short_description = 'Внешняя информация'

    def trade_names_count(self, obj):
        return obj.trade_names.count()
    trade_names_count.short_description = 'Торговых названий'

    def trade_names_link(self, obj):
        count = obj.trade_names.count()
        if count > 0:
            return format_html(
                '<a href="{}?medication__id__exact={}">Просмотреть {} торговых названий</a>',
                '/admin/pharmacy/tradename/',
                obj.id,
                count
            )
        return 'Нет торговых названий'
    trade_names_link.short_description = 'Действия'


# TradeNameInline уже определен выше для MedicationAdmin


@admin.register(TradeName)
class TradeNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'medication_info', 'medication_group', 'atc_code', 'release_form', 'external_info_link', 'medication_link', 'regimens_link')
    list_filter = ('medication', 'medication_group', 'release_form')
    search_fields = ('name', 'medication__name', 'atc_code')
    autocomplete_fields = ('medication', 'medication_group', 'release_form')
    readonly_fields = ('regimens_info',)
    list_per_page = 50

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.medication:
            # Добавляем секцию со схемами применения
            fieldsets = list(fieldsets) if fieldsets else []
            fieldsets.append(('Схемы применения', {
                'fields': ('regimens_info',),
                'classes': ('collapse',),
                'description': 'Схемы применения для препарата (МНН)'
            }))
        return fieldsets

    def regimens_info(self, obj):
        if not obj.medication:
            return 'Нет связанного препарата'
        
        regimens = obj.medication.regimens.all()
        if not regimens:
            return 'Нет схем применения для этого препарата'
        
        # Используем встроенные возможности Django admin
        from django.contrib.admin.utils import display_for_field
        
        result = []
        for regimen in regimens:
            # Заголовок схемы
            regimen_info = f"📋 {regimen.name}"
            
            # Показания
            indications = regimen.indications.all()[:3]
            if indications:
                indication_codes = [f"{ind.code}" for ind in indications]
                regimen_info += f"\n🏥 Показания: {', '.join(indication_codes)}"
                if regimen.indications.count() > 3:
                    regimen_info += f" (и еще {regimen.indications.count() - 3})"
            
            # Критерии пациента
            criteria = regimen.population_criteria.all()
            if criteria:
                regimen_info += f"\n👥 Критерии пациента: {criteria.count()} групп"
            
            # Инструкции по дозированию
            instructions = regimen.dosing_instructions.all()
            if instructions:
                regimen_info += f"\n💊 Инструкции: {instructions.count()} вариантов"
                for instruction in instructions:
                    route = f" ({instruction.route.name})" if instruction.route else ""
                    regimen_info += f"\n  • {instruction.get_dose_type_display()}: {instruction.dose_description} - {instruction.frequency_description} - {instruction.duration_description}{route}"
            
            # Корректировки
            adjustments = regimen.adjustments.all()
            if adjustments:
                regimen_info += f"\n⚠️ Корректировки: {adjustments.count()} условий"
            
            result.append(regimen_info)
        
        return format_html('<br><br>'.join(result))
    
    regimens_info.short_description = 'Схемы применения'

    def medication_info(self, obj):
        if obj.medication:
            medication_text = obj.medication.name
            if obj.medication.external_info_url:
                medication_text = format_html(
                    '<a href="{}" target="_blank">{}</a>',
                    obj.medication.external_info_url,
                    obj.medication.name
                )
            return format_html(
                '<strong>{}</strong><br><small>МНН</small>',
                medication_text
            )
        return '—'
    medication_info.short_description = 'Препарат (МНН)'

    def medication_link(self, obj):
        if obj.medication:
            return format_html(
                '<a href="{}">Просмотреть препарат</a>',
                f'/admin/pharmacy/medication/{obj.medication.id}/change/'
            )
        return '—'
    medication_link.short_description = 'Действия'

    def regimens_link(self, obj):
        if obj.medication:
            count = obj.medication.regimens.count()
            if count > 0:
                return format_html(
                    '<a href="{}?medication__id__exact={}">Просмотреть {} схем</a>',
                    '/admin/pharmacy/regimen/',
                    obj.medication.id,
                    count
                )
        return 'Нет схем'
    regimens_link.short_description = 'Схемы применения'

    def external_info_link(self, obj):
        if obj.external_info_url:
            return format_html('<a href="{}" target="_blank">Ссылка</a>', obj.external_info_url)
        return '—'
    external_info_link.short_description = 'Внешняя информация'


class PopulationCriteriaInline(admin.TabularInline):
    model = PopulationCriteria
    extra = 1
    fields = ('name', 'min_age_days', 'max_age_days', 'min_weight_kg', 'max_weight_kg')


class DosingInstructionInline(admin.TabularInline):
    model = DosingInstruction
    extra = 1
    fields = ('dose_type', 'dose_description', 'frequency_description', 'duration_description', 'route')


class RegimenAdjustmentInline(admin.TabularInline):
    model = RegimenAdjustment
    extra = 1
    fields = ('condition', 'adjustment_description')


@admin.register(Regimen)
class RegimenAdmin(admin.ModelAdmin):
    list_display = ('name', 'medication', 'indications_count', 'population_criteria_count', 'dosing_instructions_count')
    list_filter = ('medication', 'indications')
    search_fields = ('name', 'medication__name', 'indications__name', 'indications__code')
    autocomplete_fields = ('medication', 'indications')
    inlines = [PopulationCriteriaInline, DosingInstructionInline, RegimenAdjustmentInline]
    list_per_page = 20

    def indications_count(self, obj):
        return obj.indications.count()
    indications_count.short_description = 'Показаний'

    def population_criteria_count(self, obj):
        return obj.population_criteria.count()
    population_criteria_count.short_description = 'Критериев'

    def dosing_instructions_count(self, obj):
        return obj.dosing_instructions.count()
    dosing_instructions_count.short_description = 'Инструкций'


@admin.register(PopulationCriteria)
class PopulationCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'regimen', 'age_range', 'weight_range')
    list_filter = ('regimen__medication',)
    search_fields = ('name', 'regimen__name', 'regimen__medication__name')
    autocomplete_fields = ('regimen',)
    list_per_page = 50

    def age_range(self, obj):
        if obj.min_age_days and obj.max_age_days:
            return f"{obj.min_age_days}-{obj.max_age_days} дней"
        elif obj.min_age_days:
            return f"от {obj.min_age_days} дней"
        elif obj.max_age_days:
            return f"до {obj.max_age_days} дней"
        return '—'
    age_range.short_description = 'Возрастной диапазон'

    def weight_range(self, obj):
        if obj.min_weight_kg and obj.max_weight_kg:
            return f"{obj.min_weight_kg}-{obj.max_weight_kg} кг"
        elif obj.min_weight_kg:
            return f"от {obj.min_weight_kg} кг"
        elif obj.max_weight_kg:
            return f"до {obj.max_weight_kg} кг"
        return '—'
    weight_range.short_description = 'Весовая категория'


@admin.register(DosingInstruction)
class DosingInstructionAdmin(admin.ModelAdmin):
    list_display = ('regimen', 'dose_type', 'dose_description', 'frequency_description', 'duration_description', 'route')
    list_filter = ('dose_type', 'route', 'regimen__medication')
    search_fields = ('regimen__name', 'regimen__medication__name', 'dose_description')
    autocomplete_fields = ('regimen', 'route')
    list_per_page = 50


@admin.register(RegimenAdjustment)
class RegimenAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('regimen', 'condition', 'adjustment_description')
    list_filter = ('regimen__medication',)
    search_fields = ('regimen__name', 'regimen__medication__name', 'condition')
    autocomplete_fields = ('regimen',)
    list_per_page = 50


# Настройка админки
admin.site.site_header = "Администрирование медицинской системы"
admin.site.site_title = "Медицинская система"
admin.site.index_title = "Панель управления"
