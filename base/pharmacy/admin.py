from django.contrib import admin
from .models import Medication, DosingRule


# 1. Создаем "встраиваемый" редактор для правил дозирования
# TabularInline делает отображение компактным, в виде таблицы
class DosingRuleInline(admin.TabularInline):
    model = DosingRule

    # Определяем, какие поля и в каком порядке показывать в форме
    fields = (
        'name',
        'route_of_administration',
        ('min_age_days', 'max_age_days'),
        ('min_weight_kg', 'max_weight_kg'),
        ('dosage_value', 'dosage_unit'),
        'frequency_text',
        'max_daily_dosage_text',
        'notes',
        'is_loading_dose',
    )

    # По умолчанию показывать 1 пустую форму для добавления нового правила
    extra = 1


# 2. Настраиваем основную админ-панель для препаратов
@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    # Обновляем поля для отображения в списке
    list_display = ('name', 'form')
    search_fields = ('name', 'form')

    # 3. "Встраиваем" редактор правил в страницу препарата
    inlines = [DosingRuleInline]