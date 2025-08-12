# pharmacy/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q

from diagnosis.models import Diagnosis 
from patients.models import Patient 

class MedicationGroup(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name=_("Название группы"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание группы"))
    
    class Meta:
        verbose_name = _("Группа препаратов")
        verbose_name_plural = _("Группы препаратов")
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_or_create_smart(cls, name, description=None):
        """
        Умный метод для получения или создания группы препаратов.
        Автоматически создает новую группу, если она не существует.
        """
        try:
            group = cls.objects.get(name=name)
            return group, False
        except cls.DoesNotExist:
            group = cls.objects.create(
                name=name,
                description=description or f"Автоматически созданная группа: {name}"
            )
            return group, True

class ReleaseForm(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название формы выпуска"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание формы выпуска"))
    
    class Meta:
        verbose_name = _("Форма выпуска")
        verbose_name_plural = _("Формы выпуска")
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_or_create_smart(cls, name, description=None):
        """
        Умный метод для получения или создания формы выпуска.
        Автоматически создает новую форму, если она не существует.
        """
        try:
            form = cls.objects.get(name=name)
            return form, False
        except cls.DoesNotExist:
            form = cls.objects.create(
                name=name,
                description=description or f"Автоматически созданная форма выпуска: {name}"
            )
            return form, True

class AdministrationMethod(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название способа введения"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание способа введения"))
    
    class Meta:
        verbose_name = _("Способ введения")
        verbose_name_plural = _("Способы введения")
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_or_create_smart(cls, name, description=None):
        """
        Умный метод для получения или создания способа введения.
        Автоматически создает новый способ, если он не существует.
        
        Args:
            name (str): Название способа введения
            description (str, optional): Описание способа введения
            
        Returns:
            tuple: (AdministrationMethod, created) - объект и флаг создания
        """
        try:
            # Пытаемся найти существующий способ
            method = cls.objects.get(name=name)
            return method, False
        except cls.DoesNotExist:
            # Если не найден - создаем новый
            method = cls.objects.create(
                name=name,
                description=description or f"Автоматически созданный способ введения: {name}"
            )
            return method, True

class MedicationQuerySet(models.QuerySet):
    """Набор кастомных методов для фильтрации."""
    
    def active(self):
        """Возвращает только активные препараты."""
        return self.filter(is_active=True)

    def generics(self):
        """Возвращает только МНН/концепты."""
        return self.filter(generic_concept__isnull=True)

    def trade_products(self):
        """Возвращает только торговые препараты."""
        return self.filter(generic_concept__isnull=False)

    def by_generic(self, generic_name):
        """Найти все торговые продукты по МНН."""
        return self.filter(generic_concept__name=generic_name)

    def with_forms(self, *forms):
        """Фильтр по лекарственным формам."""
        return self.filter(medication_form__in=forms)

    def by_code_system(self, code_system):
        """Фильтр по системе кодирования."""
        return self.filter(code_system=code_system)


class MedicationManager(models.Manager):
    """Кастомный менеджер для модели."""
    
    def get_queryset(self):
        return MedicationQuerySet(self.model, using=self._db)

    # Добавляем прямые доступы к методам QuerySet
    def active(self):
        return self.get_queryset().active()
        
    def generics(self):
        return self.get_queryset().generics()
        
    def trade_products(self):
        return self.get_queryset().trade_products()
        
    def by_generic(self, generic_name):
        return self.get_queryset().by_generic(generic_name)
        
    def with_forms(self, *forms):
        return self.get_queryset().with_forms(*forms)
        
    def by_code_system(self, code_system):
        return self.get_queryset().by_code_system(code_system)


class Medication(models.Model):
    """
    Модель-справочник. Хранит только основную информацию о препарате.
    """
    
    # Создаем классы для хранения констант
    class MedicationForm(models.TextChoices):
        TABLET = 'tablet', _('Таблетки')
        CAPSULE = 'capsule', _('Капсулы')
        SOLUTION = 'solution', _('Раствор')
        OINTMENT = 'ointment', _('Мазь')
        SUPPOSITORY = 'suppository', _('Суппозитории')
        GEL = 'gel', _('Гель')
        CREAM = 'cream', _('Крем')
        SYRUP = 'syrup', _('Сироп')
        SUSPENSION = 'suspension', _('Суспензия')
        POWDER = 'powder', _('Порошок')
        INJECTION = 'injection', _('Инъекции')
        DROPS = 'drops', _('Капли')
        SPRAY = 'spray', _('Спрей')
        PATCH = 'patch', _('Пластырь')
        INHALER = 'inhaler', _('Ингалятор')

    class CodeSystem(models.TextChoices):
        ATC = 'atc', _('АТХ (Анатомо-терапевтическо-химическая классификация)')
        RXNORM = 'rxnorm', _('RxNorm')
        SNOMED = 'snomed', _('SNOMED CT')
        ICD10 = 'icd10', _('МКБ-10')
        WHO = 'who', _('ВОЗ')
        LOCAL = 'local', _('Локальная система')

    id = models.AutoField(primary_key=True)
    name = models.CharField("Название препарата (МНН)", max_length=255, unique=True,
                            help_text="Международное непатентованное наименование")
    
    # Применяем choices к полям
    medication_form = models.CharField(
        max_length=100, 
        choices=MedicationForm.choices,
        blank=True,
        verbose_name=_("Лекарственная форма")
    )
    code_system = models.CharField(
        max_length=50, 
        choices=CodeSystem.choices,
        default=CodeSystem.ATC,
        verbose_name=_("Система кодирования")
    )
    code = models.CharField(max_length=50, blank=True, verbose_name=_("Код препарата"))
    
    # Ссылка на внешний источник полной информации
    external_info_url = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Ссылка на полную информацию о препарате"))
    
    # ДОБАВЛЯЕМ ЭТО ПОЛЕ - связь МНН и торговых названий
    generic_concept = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Основа (МНН)"),
        help_text=_("Если это торговый препарат, укажите его действующее вещество (МНН) из этой же таблицы.")
    )
    
    # Добавляем поле для торгового названия
    trade_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_("Торговое название"),
        help_text=_("Торговое название препарата (если отличается от МНН)")
    )
    
    # Добавляем поле активности
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))

    class Meta:
        verbose_name = "Препарат"
        verbose_name_plural = "Препараты"
        ordering = ['name']
    
    # Добавляем наш новый менеджер
    objects = MedicationManager()

    def __str__(self):
        # Немного улучшим строковое представление
        if self.generic_concept:
            # Это торговый продукт
            return f"{self.trade_name} ({self.name})"
        else:
            # Это концепт/МНН
            return self.name
    
    def is_generic(self):
        """Это МНН/действующее вещество?"""
        return self.generic_concept is None

    def is_trade_product(self):
        """Это торговый продукт?"""
        return self.generic_concept is not None

    def get_display_name(self):
        """Полное название для отображения"""
        if self.is_trade_product():
            return f"{self.trade_name} ({self.generic_concept.name})"
        return self.name

class TradeName(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Название"))
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='trade_names', verbose_name=_("МНН"))
    medication_group = models.ForeignKey(MedicationGroup, on_delete=models.CASCADE, verbose_name=_("Группа препаратов"))
    release_form = models.ForeignKey(ReleaseForm, on_delete=models.CASCADE, verbose_name=_("Форма выпуска"))
    atc_code = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("ATC код"))
    external_info_url = models.URLField(blank=True, null=True, verbose_name=_("Внешняя ссылка"))
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Торговое название")
        verbose_name_plural = _("Торговые названия")
        unique_together = ['name', 'medication']

    def __str__(self):
        return f"{self.name} ({self.medication.name})"

class RegimenManager(models.Manager):
    """
    Менеджер для модели Regimen с оптимизированными методами фильтрации
    """
    
    def get_suitable_for_patient(self, medication, patient=None, release_form=None):
        """
        Получает схемы применения, подходящие для пациента и формы выпуска
        
        Args:
            medication: Препарат
            patient: Пациент (опционально)
            release_form: Форма выпуска (опционально)
            
        Returns:
            QuerySet: Подходящие схемы применения
        """
        # Базовый фильтр: только схемы с инструкциями по дозировке
        queryset = self.filter(
            medication=medication,
            dosing_instructions__isnull=False
        ).distinct()
        
        # Если нет данных о пациенте, возвращаем все схемы с инструкциями
        if not patient or not patient.birth_date:
            return queryset
        
        from datetime import date
        
        age_days = (date.today() - patient.birth_date).days
        patient_weight = getattr(patient, 'weight', None)
        
        # Условия для фильтрации по возрасту
        age_filter = (
            Q(population_criteria__min_age_days__lte=age_days) |
            Q(population_criteria__min_age_days__isnull=True)
        ) & (
            Q(population_criteria__max_age_days__gte=age_days) |
            Q(population_criteria__max_age_days__isnull=True)
        )
        
        # Условия для фильтрации по весу
        weight_filter = Q()
        if patient_weight:
            weight_filter = (
                Q(population_criteria__min_weight_kg__lte=patient_weight) |
                Q(population_criteria__min_weight_kg__isnull=True)
            ) & (
                Q(population_criteria__max_weight_kg__gte=patient_weight) |
                Q(population_criteria__max_weight_kg__isnull=True)
            )
        
        # Фильтруем схемы, которые либо не имеют критериев, либо соответствуют им
        return queryset.filter(
            Q(population_criteria__isnull=True) | (age_filter & weight_filter)
        ).distinct()
    
    def get_compatible_with_form(self, medication, release_form):
        """
        Получает схемы применения, совместимые с формой выпуска
        
        Args:
            medication: Препарат
            release_form: Форма выпуска
            
        Returns:
            QuerySet: Совместимые схемы применения
        """
        if not release_form:
            return self.filter(
                medication=medication,
                dosing_instructions__isnull=False
            ).distinct()
        
        # Базовый фильтр по препарату и наличию инструкций
        queryset = self.filter(
            medication=medication,
            dosing_instructions__isnull=False
        ).distinct()
        
        # Используем новое поле compatible_forms для проверки совместимости
        # Если у инструкции не указаны совместимые формы, считаем её совместимой со всеми
        compatible_regimens = queryset.filter(
            Q(dosing_instructions__compatible_forms=release_form) |
            Q(dosing_instructions__compatible_forms__isnull=True)
        ).distinct()
        
        return compatible_regimens


class Regimen(models.Model):
    """
    Схема (режим) применения препарата для определённого клинического случая.
    Это центральная модель, объединяющая показания, критерии и дозировки.
    """
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='regimens',
                                   verbose_name=_("Препарат (МНН)"))
    
    name = models.CharField(_("Название схемы"), max_length=255, 
                            help_text=_("Напр., 'Стандартная терапия для взрослых' или 'Терапия неосложненной гонореи'"))

    indications = models.ManyToManyField(Diagnosis, related_name='regimens', 
                                         verbose_name=_("Показания (Диагнозы)"),
                                         help_text=_("Диагнозы, при которых применяется эта схема"))

    notes = models.TextField(_("Общие примечания к схеме"), blank=True, null=True)
    
    # Используем кастомный менеджер
    objects = RegimenManager()

    class Meta:
        verbose_name = _("Схема применения")
        verbose_name_plural = _("Схемы применения")
        ordering = ['medication', 'name']

    def __str__(self):
        return f"{self.medication.name} - {self.name}"


class PopulationCriteria(models.Model):
    """
    Описывает целевую группу пациентов для конкретной схемы применения.
    У одной схемы может быть несколько наборов критериев.
    """
    regimen = models.ForeignKey(Regimen, on_delete=models.CASCADE, related_name='population_criteria',
                                verbose_name=_("Схема применения"))
    
    name = models.CharField(_("Название группы пациентов"), max_length=255, default="Основная группа",
                            help_text=_("Напр., 'Взрослые и дети > 12 лет', 'Дети 6-12 лет'"))

    min_age_days = models.PositiveIntegerField(_("Минимальный возраст (дней)"), blank=True, null=True)
    max_age_days = models.PositiveIntegerField(_("Максимальный возраст (дней)"), blank=True, null=True)

    min_weight_kg = models.DecimalField(_("Минимальный вес (кг)"), max_digits=5, decimal_places=2, blank=True, null=True)
    max_weight_kg = models.DecimalField(_("Максимальный вес (кг)"), max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = _("Критерии пациента")
        verbose_name_plural = _("Критерии пациентов")

    def __str__(self):
        return f"{self.regimen} - {self.name}"

    def clean(self):
        if self.min_age_days and self.max_age_days:
            if self.min_age_days > self.max_age_days:
                raise ValidationError("Минимальный возраст не может быть больше максимального")


class DosingInstruction(models.Model):
    """
    Конкретная инструкция по дозированию в рамках одной схемы.
    """
    regimen = models.ForeignKey(Regimen, on_delete=models.CASCADE, related_name='dosing_instructions',
                                verbose_name=_("Схема применения"))

    DOSE_TYPE_CHOICES = [
        ('MAINTENANCE', _('Поддерживающая')),
        ('LOADING', _('Нагрузочная')),
        ('SINGLE', _('Однократная')),
    ]
    dose_type = models.CharField(_("Тип дозы"), max_length=20, choices=DOSE_TYPE_CHOICES, default='MAINTENANCE')

    # Использование текстового поля дает гибкость для описания сложных доз
    dose_description = models.CharField(_("Описание дозы"), max_length=255, 
                                        help_text=_("Напр., '400 мг' или '8 мг/кг массы тела'"))
    
    frequency_description = models.CharField(_("Описание частоты"), max_length=255, 
                                             help_text=_("Напр., '1 раз/сутки' или 'по 200 мг каждые 12 ч'"))

    duration_description = models.CharField(_("Описание длительности"), max_length=255,
                                            help_text=_("Напр., '7-10 дней' или 'не менее 10 дней'"))

    route = models.ForeignKey(AdministrationMethod, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name=_("Путь введения"))
    
    # Явно указываем, для каких форм выпуска подходит эта инструкция
    compatible_forms = models.ManyToManyField(
        'ReleaseForm',
        blank=True,
        verbose_name=_("Совместимые формы выпуска"),
        help_text=_("Формы выпуска, для которых подходит эта инструкция по дозированию")
    )

    class Meta:
        verbose_name = _("Инструкция по дозированию")
        verbose_name_plural = _("Инструкции по дозированию")

    def __str__(self):
        return f"{self.regimen} - {self.dose_description}"


class RegimenAdjustment(models.Model):
    """
    Корректировка базовой схемы при определённых условиях.
    """
    regimen = models.ForeignKey(Regimen, on_delete=models.CASCADE, related_name='adjustments',
                                verbose_name=_("Схема применения"))

    condition = models.CharField(_("Условие для корректировки"), max_length=255, 
                                 help_text=_("Напр., 'При КК от 21 до 60 мл/мин' или 'Пациенты на гемодиализе'"))

    adjustment_description = models.CharField(_("Описание корректировки"), max_length=255,
                                              help_text=_("Напр., 'суточную дозу следует уменьшить на 25%'"))
    
    class Meta:
        verbose_name = _("Корректировка схемы")
        verbose_name_plural = _("Корректировки схем")

    def __str__(self):
        return f"Корректировка для '{self.regimen.name}'"