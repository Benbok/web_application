from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.contrib.admin import SimpleListFilter
from .models import (
    MedicationGroup, ReleaseForm, AdministrationMethod, Medication, 
    TradeName, Regimen, PopulationCriteria, DosingInstruction, RegimenAdjustment
)


# Кастомные фильтры
class HasTradeNamesFilter(SimpleListFilter):
    title = 'Наличие торговых названий'
    parameter_name = 'has_trade_names'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть торговые названия'),
            ('no', 'Нет торговых названий'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(trade_names__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(trade_names__isnull=True)
        return queryset


class HasRegimensFilter(SimpleListFilter):
    title = 'Наличие схем применения'
    parameter_name = 'has_regimens'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть схемы применения'),
            ('no', 'Нет схем применения'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(regimens__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(regimens__isnull=True)
        return queryset


class AgeGroupFilter(SimpleListFilter):
    title = 'Возрастная группа'
    parameter_name = 'age_group'

    def lookups(self, request, model_admin):
        return (
            ('children', 'Дети (до 18 лет)'),
            ('adults', 'Взрослые (18+ лет)'),
            ('elderly', 'Пожилые (65+ лет)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'children':
            return queryset.filter(max_age_days__lte=6570)  # 18 лет * 365 дней
        if self.value() == 'adults':
            return queryset.filter(min_age_days__gte=6570)
        if self.value() == 'elderly':
            return queryset.filter(min_age_days__gte=23725)  # 65 лет * 365 дней
        return queryset


# Действия для админки
@admin.register(MedicationGroup)
class MedicationGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview', 'medications_count', 'medications_link')
    search_fields = ('name', 'description')
    list_per_page = 50
    actions = ['duplicate_group']
    readonly_fields = ('medications_info',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            # Добавляем секцию с препаратами
            fieldsets = list(fieldsets) if fieldsets else []
            fieldsets.append(('Препараты в этой группе', {
                'fields': ('medications_info',),
                'classes': ('collapse',),
                'description': 'Список всех препаратов, относящихся к данной группе'
            }))
        return fieldsets

    def medications_count(self, obj):
        # Получаем количество торговых названий в этой группе
        return obj.tradename_set.count()
    medications_count.short_description = 'Препаратов в группе'

    def medications_link(self, obj):
        count = obj.tradename_set.count()
        if count > 0:
            return format_html(
                '<a href="{}?medication_group__id__exact={}">Просмотреть {} препаратов</a>',
                '/admin/pharmacy/tradename/',
                obj.id,
                count
            )
        return 'Нет препаратов'
    medications_link.short_description = 'Действия'

    def medications_info(self, obj):
        # Получаем все торговые названия в этой группе
        trade_names = obj.tradename_set.all()
        
        if not trade_names.exists():
            return 'В этой группе нет препаратов'
        
        result = []
        for trade_name in trade_names:
            medication = trade_name.medication
            
            # Создаем ссылку на препарат
            medication_link = format_html(
                '<a href="{}">💊 {}</a>',
                f'/admin/pharmacy/tradename/{trade_name.id}/change/',
                medication.name
            )
            
            result.append(medication_link)
        
        return format_html('<br>'.join(result))
    
    medications_info.short_description = 'Препараты в группе'

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return '—'
    description_preview.short_description = 'Описание'

    def duplicate_group(self, request, queryset):
        for group in queryset:
            new_group = MedicationGroup.objects.create(
                name=f"{group.name} (копия)",
                description=group.description
            )
        self.message_user(request, f"Создано {queryset.count()} копий групп")
    duplicate_group.short_description = "Дублировать выбранные группы"


@admin.register(ReleaseForm)
class ReleaseFormAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview', 'medications_count')
    search_fields = ('name', 'description')
    list_per_page = 50

    def medications_count(self, obj):
        # Получаем количество торговых названий с этой формой выпуска
        return obj.tradename_set.count()
    medications_count.short_description = 'Препаратов в форме'

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return '—'
    description_preview.short_description = 'Описание'


@admin.register(AdministrationMethod)
class AdministrationMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview', 'medications_count', 'medications_link')
    search_fields = ('name', 'description')
    list_per_page = 50
    readonly_fields = ('medications_info',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            # Добавляем секцию с препаратами
            fieldsets = list(fieldsets) if fieldsets else []
            fieldsets.append(('Препараты с этим способом введения', {
                'fields': ('medications_info',),
                'classes': ('collapse',),
                'description': 'Список препаратов, использующих данный способ введения'
            }))
        return fieldsets

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return '—'
    description_preview.short_description = 'Описание'

    def medications_count(self, obj):
        # Подсчитываем количество препаратов через схемы применения
        return DosingInstruction.objects.filter(route=obj).values('regimen__medication').distinct().count()
    medications_count.short_description = 'Препаратов'

    def medications_link(self, obj):
        count = self.medications_count(obj)
        if count > 0:
            return format_html(
                '<a href="{}?route__id__exact={}">Просмотреть {} препаратов</a>',
                '/admin/pharmacy/dosinginstruction/',
                obj.id,
                count
            )
        return 'Нет препаратов'
    medications_link.short_description = 'Действия'

    def medications_info(self, obj):
        # Получаем все препараты через схемы применения
        medications = DosingInstruction.objects.filter(route=obj).values(
            'regimen__medication__name', 
            'regimen__medication__id'
        ).distinct()
        
        if not medications:
            return 'Нет препаратов с данным способом введения'
        
        result = []
        for med_data in medications:
            medication_name = med_data['regimen__medication__name']
            medication_id = med_data['regimen__medication__id']
            
            # Создаем ссылку на препарат
            medication_link = format_html(
                '<a href="{}">💊 {}</a>',
                f'/admin/pharmacy/medication/{medication_id}/change/',
                medication_name
            )
            
            result.append(medication_link)
        
        return format_html('<br>'.join(result))
    
    medications_info.short_description = 'Препараты'





@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'medication_type', 'medication_form', 'is_active', 'external_info_link', 'regimens_count')
    search_fields = ('name', 'trade_name', 'generic_concept__name')
    list_filter = ('is_active', 'medication_form', 'code_system')
    list_per_page = 50
    actions = ['add_external_info_template']
    readonly_fields = ('regimens_info', 'statistics_info')
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            # Добавляем секции с дополнительной информацией
            fieldsets = list(fieldsets) if fieldsets else []
            fieldsets.extend([
                ('Схемы применения', {
                    'fields': ('regimens_info',),
                    'classes': ('collapse',),
                    'description': 'Все схемы применения препарата с детальной информацией'
                }),
                ('Статистика', {
                    'fields': ('statistics_info',),
                    'classes': ('collapse',),
                    'description': 'Общая статистика по препарату'
                })
            ])
        return fieldsets

    def medication_type(self, obj):
        if obj.is_trade_product():
            return f"Торговый продукт ({obj.generic_concept.name})"
        else:
            return "МНН (действующее вещество)"
    medication_type.short_description = 'Тип препарата'
    
    def external_info_link(self, obj):
        if obj.external_info_url:
            return format_html('<a href="{}" target="_blank">Ссылка</a>', obj.external_info_url)
        return '—'
    external_info_link.short_description = 'Внешняя информация'

    def regimens_count(self, obj):
        return obj.regimens.count()
    regimens_count.short_description = 'Схем применения'
    
    def regimens_info(self, obj):
        """Детальная информация о схемах применения"""
        regimens = obj.regimens.all()
        
        if not regimens.exists():
            return 'Нет схем применения для этого препарата'
        
        result = []
        for regimen in regimens:
            regimen_info = f"📋 {regimen.name}"
            
            # Показания
            indications = regimen.indications.all()
            if indications:
                indication_codes = [f"{ind.code} - {ind.name}" for ind in indications[:5]]
                regimen_info += f"\n🏥 Показания: {', '.join(indication_codes)}"
                if indications.count() > 5:
                    regimen_info += f" (и еще {indications.count() - 5})"
            
            # Критерии пациента
            criteria = regimen.population_criteria.all()
            if criteria:
                regimen_info += f"\n👥 Критерии пациента: {criteria.count()} групп"
                for criterion in criteria[:3]:
                    age_info = ""
                    if criterion.min_age_days and criterion.max_age_days:
                        age_info = f"{criterion.min_age_days}-{criterion.max_age_days} дней"
                    elif criterion.min_age_days:
                        age_info = f"от {criterion.min_age_days} дней"
                    elif criterion.max_age_days:
                        age_info = f"до {criterion.max_age_days} дней"
                    
                    weight_info = ""
                    if criterion.min_weight_kg and criterion.max_weight_kg:
                        weight_info = f"{criterion.min_weight_kg}-{criterion.max_weight_kg} кг"
                    elif criterion.min_weight_kg:
                        weight_info = f"от {criterion.min_weight_kg} кг"
                    elif criterion.max_weight_kg:
                        weight_info = f"до {criterion.max_weight_kg} кг"
                    
                    if age_info or weight_info:
                        regimen_info += f"\n  • {criterion.name}: {age_info} {weight_info}".strip()
            
            # Инструкции по дозированию
            instructions = regimen.dosing_instructions.all()
            if instructions:
                regimen_info += f"\n💊 Инструкции по дозированию: {instructions.count()} вариантов"
                for instruction in instructions:
                    route = f" ({instruction.route.name})" if instruction.route else ""
                    regimen_info += f"\n  • {instruction.get_dose_type_display()}: {instruction.dose_description}"
                    regimen_info += f"\n    Частота: {instruction.frequency_description}"
                    regimen_info += f"\n    Длительность: {instruction.duration_description}{route}"
            
            # Корректировки
            adjustments = regimen.adjustments.all()
            if adjustments:
                regimen_info += f"\n⚠️ Корректировки: {adjustments.count()} условий"
                for adjustment in adjustments[:3]:
                    regimen_info += f"\n  • {adjustment.condition}: {adjustment.adjustment_description}"
            
            # Ссылка на редактирование
            regimen_info += f"\n✏️ <a href='/admin/pharmacy/regimen/{regimen.id}/change/'>Редактировать схему</a>"
            
            result.append(regimen_info)
        
        return format_html('<br><br>'.join(result))
    
    regimens_info.short_description = 'Схемы применения'
    
    def statistics_info(self, obj):
        """Общая статистика по препарату"""
        regimens_count = obj.regimens.count()
        
        # Подсчет уникальных показаний
        all_indications = set()
        for regimen in obj.regimens.all():
            all_indications.update(regimen.indications.all())
        indications_count = len(all_indications)
        
        # Подсчет уникальных способов введения
        all_routes = set()
        for regimen in obj.regimens.all():
            for instruction in regimen.dosing_instructions.all():
                if instruction.route:
                    all_routes.add(instruction.route)
        routes_count = len(all_routes)
        
        # Определяем тип препарата
        if obj.is_trade_product():
            medication_type = f"Торговый продукт ({obj.generic_concept.name})"
        else:
            medication_type = "МНН (действующее вещество)"
        
        stats = f"""
        📊 <strong>Общая статистика препарата "{obj.name}"</strong><br><br>
        
        💊 <strong>Тип препарата:</strong> {medication_type}<br>
        📋 <strong>Схемы применения:</strong> {regimens_count}<br>
        🏥 <strong>Уникальных показаний:</strong> {indications_count}<br>
        💉 <strong>Способов введения:</strong> {routes_count}<br>
        💊 <strong>Форма выпуска:</strong> {obj.medication_form or 'Не указана'}<br>
        """
        
        # Дополнительная информация
        if obj.external_info_url:
            stats += f"<br>🔗 <a href='{obj.external_info_url}' target='_blank'>Внешняя информация о препарате</a>"
        
        return format_html(stats)
    
    statistics_info.short_description = 'Статистика'

    def add_external_info_template(self, request, queryset):
        updated = 0
        for medication in queryset:
            if not medication.external_info_url:
                # Создаем шаблонную ссылку на поиск в Google
                search_query = f"{medication.name} инструкция по применению"
                google_search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                medication.external_info_url = google_search_url
                medication.save()
                updated += 1
        self.message_user(request, f"Добавлено {updated} ссылок на внешнюю информацию")
    add_external_info_template.short_description = "Добавить ссылки на внешнюю информацию"


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
    fields = ('dose_type', 'dose_description', 'frequency_description', 'duration_description', 'route', 'compatible_forms')


class RegimenAdjustmentInline(admin.TabularInline):
    model = RegimenAdjustment
    extra = 1
    fields = ('condition', 'adjustment_description')


@admin.register(Regimen)
class RegimenAdmin(admin.ModelAdmin):
    list_display = ('name', 'medication', 'indications_count', 'population_criteria_count', 'dosing_instructions_count', 'completeness_score')
    list_filter = ('medication', 'indications', 'dosing_instructions__dose_type')
    search_fields = ('name', 'medication__name', 'indications__name', 'indications__code')
    autocomplete_fields = ('medication', 'indications')
    inlines = [PopulationCriteriaInline, DosingInstructionInline, RegimenAdjustmentInline]
    list_per_page = 20
    actions = ['duplicate_regimen']

    def indications_count(self, obj):
        return obj.indications.count()
    indications_count.short_description = 'Показаний'

    def population_criteria_count(self, obj):
        return obj.population_criteria.count()
    population_criteria_count.short_description = 'Критериев'

    def dosing_instructions_count(self, obj):
        return obj.dosing_instructions.count()
    dosing_instructions_count.short_description = 'Инструкций'

    def completeness_score(self, obj):
        """Оценка полноты схемы (0-100%)"""
        score = 0
        total = 4  # Общее количество компонентов
        
        if obj.indications.exists():
            score += 1
        if obj.population_criteria.exists():
            score += 1
        if obj.dosing_instructions.exists():
            score += 1
        if obj.adjustments.exists():
            score += 1
        
        percentage = (score / total) * 100
        
        if percentage >= 75:
            color = 'green'
        elif percentage >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            int(percentage)
        )
    completeness_score.short_description = 'Полнота'

    def duplicate_regimen(self, request, queryset):
        for regimen in queryset:
            # Создаем копию схемы
            new_regimen = Regimen.objects.create(
                medication=regimen.medication,
                name=f"{regimen.name} (копия)",
                notes=regimen.notes
            )
            
            # Копируем показания
            new_regimen.indications.set(regimen.indications.all())
            
            # Копируем критерии пациента
            for criteria in regimen.population_criteria.all():
                PopulationCriteria.objects.create(
                    regimen=new_regimen,
                    name=criteria.name,
                    min_age_days=criteria.min_age_days,
                    max_age_days=criteria.max_age_days,
                    min_weight_kg=criteria.min_weight_kg,
                    max_weight_kg=criteria.max_weight_kg
                )
            
            # Копируем инструкции по дозированию
            for instruction in regimen.dosing_instructions.all():
                DosingInstruction.objects.create(
                    regimen=new_regimen,
                    dose_type=instruction.dose_type,
                    dose_description=instruction.dose_description,
                    frequency_description=instruction.frequency_description,
                    duration_description=instruction.duration_description,
                    route=instruction.route
                )
            
            # Копируем корректировки
            for adjustment in regimen.adjustments.all():
                RegimenAdjustment.objects.create(
                    regimen=new_regimen,
                    condition=adjustment.condition,
                    adjustment_description=adjustment.adjustment_description
                )
        
        self.message_user(request, f"Создано {queryset.count()} копий схем")
    duplicate_regimen.short_description = "Дублировать выбранные схемы"


@admin.register(PopulationCriteria)
class PopulationCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'regimen', 'age_range', 'weight_range', 'patient_count_estimate')
    list_filter = ('regimen__medication', AgeGroupFilter)
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

    def patient_count_estimate(self, obj):
        """Примерная оценка количества пациентов, подходящих под критерии"""
        # Это упрощенная оценка для демонстрации
        if obj.min_age_days and obj.max_age_days:
            age_range = obj.max_age_days - obj.min_age_days
            if age_range < 365:  # Меньше года
                return "Небольшая группа"
            elif age_range < 3650:  # Меньше 10 лет
                return "Средняя группа"
            else:
                return "Большая группа"
        return "Неопределено"
    patient_count_estimate.short_description = 'Оценка группы'


@admin.register(DosingInstruction)
class DosingInstructionAdmin(admin.ModelAdmin):
    list_display = ('regimen', 'dose_type', 'dose_description', 'frequency_description', 'duration_description', 'route', 'compatible_forms_count', 'completeness_indicator')
    list_filter = ('dose_type', 'route', 'regimen__medication', 'compatible_forms')
    search_fields = ('regimen__name', 'regimen__medication__name', 'dose_description')
    autocomplete_fields = ('regimen', 'route', 'compatible_forms')
    list_per_page = 50

    def compatible_forms_count(self, obj):
        """Количество совместимых форм выпуска"""
        count = obj.compatible_forms.count()
        if count == 0:
            return format_html('<span style="color: gray;">Все формы</span>')
        else:
            return format_html('<span style="color: blue;">{} форм</span>', count)
    compatible_forms_count.short_description = 'Совместимые формы'

    def completeness_indicator(self, obj):
        """Индикатор полноты инструкции"""
        missing_fields = []
        if not obj.dose_description:
            missing_fields.append('доза')
        if not obj.frequency_description:
            missing_fields.append('частота')
        if not obj.duration_description:
            missing_fields.append('длительность')
        
        if not missing_fields:
            return format_html('<span style="color: green;">✓ Полная</span>')
        else:
            return format_html(
                '<span style="color: orange;">⚠ Неполная ({})</span>',
                ', '.join(missing_fields)
            )
    completeness_indicator.short_description = 'Статус'


@admin.register(RegimenAdjustment)
class RegimenAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('regimen', 'condition', 'adjustment_description', 'condition_type')
    list_filter = ('regimen__medication',)
    search_fields = ('regimen__name', 'regimen__medication__name', 'condition')
    autocomplete_fields = ('regimen',)
    list_per_page = 50

    def condition_type(self, obj):
        """Определение типа условия корректировки"""
        condition_lower = obj.condition.lower()
        if 'почк' in condition_lower or 'кк' in condition_lower or 'креатинин' in condition_lower:
            return "Почечная недостаточность"
        elif 'печен' in condition_lower or 'алт' in condition_lower or 'аст' in condition_lower:
            return "Печеночная недостаточность"
        elif 'гемодиализ' in condition_lower or 'диализ' in condition_lower:
            return "Гемодиализ"
        elif 'возраст' in condition_lower or 'пожил' in condition_lower:
            return "Возрастные особенности"
        elif 'беремен' in condition_lower or 'лактац' in condition_lower:
            return "Беременность/лактация"
        else:
            return "Другое"
    condition_type.short_description = 'Тип условия'


# Настройка админки
admin.site.site_header = "Администрирование медицинской системы"
admin.site.site_title = "Медицинская система"
admin.site.index_title = "Панель управления"
