from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import hashlib


class SignatureWorkflow(models.Model):
    """
    Модель для управления рабочим процессом подписей
    """
    WORKFLOW_TYPES = [
        ('simple', 'Простая подпись (только врач)'),
        ('standard', 'Стандартная (врач + заведующий)'),
        ('complex', 'Сложная (врач + заведующий + главный врач)'),
        ('critical', 'Критическая (врач + заведующий + главный врач + пациент)'),
    ]
    
    name = models.CharField("Название", max_length=100)
    workflow_type = models.CharField("Тип процесса", max_length=20, choices=WORKFLOW_TYPES)
    description = models.TextField("Описание", blank=True)
    
    # Настройки для каждого типа подписи
    require_doctor_signature = models.BooleanField("Требуется подпись врача", default=True)
    require_head_signature = models.BooleanField("Требуется подпись заведующего", default=False)
    require_chief_signature = models.BooleanField("Требуется подпись главного врача", default=False)
    require_patient_signature = models.BooleanField("Требуется подпись пациента", default=False)
    
    # Автоматические действия
    auto_complete_on_doctor_signature = models.BooleanField("Автозавершение при подписи врача", default=False)
    auto_complete_on_all_signatures = models.BooleanField("Автозавершение при всех подписях", default=True)
    
    # Временные ограничения (в днях)
    doctor_signature_timeout_days = models.PositiveIntegerField("Таймаут подписи врача (дни)", default=7)
    head_signature_timeout_days = models.PositiveIntegerField("Таймаут подписи заведующего (дни)", default=3)
    chief_signature_timeout_days = models.PositiveIntegerField("Таймаут подписи главного врача (дни)", default=2)
    patient_signature_timeout_days = models.PositiveIntegerField("Таймаут подписи пациента (дни)", default=5)
    
    # Дополнительные настройки
    allow_parallel_signatures = models.BooleanField("Разрешить параллельные подписи", default=False)
    require_sequential_order = models.BooleanField("Требовать последовательный порядок", default=True)
    
    # Активность
    is_active = models.BooleanField("Активен", default=True)
    
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    
    class Meta:
        verbose_name = "Рабочий процесс подписей"
        verbose_name_plural = "Рабочие процессы подписей"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_workflow_type_display()})"
    
    def clean(self):
        """Проверяем корректность настроек"""
        if not self.require_doctor_signature and not self.require_head_signature and not self.require_chief_signature and not self.require_patient_signature:
            raise ValidationError("Должен быть указан хотя бы один тип подписи")
    
    def get_required_signatures(self):
        """Возвращает список требуемых подписей в правильном порядке"""
        signatures = []
        
        if self.require_doctor_signature:
            signatures.append('doctor')
        if self.require_head_signature:
            signatures.append('head_of_department')
        if self.require_chief_signature:
            signatures.append('chief_physician')
        if self.require_patient_signature:
            signatures.append('patient')
        
        return signatures
    
    def get_next_required_signature(self, document):
        """Получает следующую требуемую подпись для документа"""
        from .models import DocumentSignature
        
        content_type = ContentType.objects.get_for_model(document)
        existing_signatures = DocumentSignature.objects.filter(
            content_type=content_type,
            object_id=document.pk
        )
        
        required_signatures = self.get_required_signatures()
        
        for signature_type in required_signatures:
            if not existing_signatures.filter(signature_type=signature_type, status='signed').exists():
                return signature_type
        
        return None


class DocumentSignature(models.Model):
    """
    Модель для хранения подписей документов
    """
    SIGNATURE_TYPES = [
        ('doctor', 'Врач-исследователь'),
        ('head_of_department', 'Заведующий отделением'),
        ('chief_physician', 'Главный врач'),
        ('patient', 'Пациент'),
        ('nurse', 'Медсестра'),
        ('technician', 'Техник'),
        ('consultant', 'Консультант'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает подписи'),
        ('signed', 'Подписано'),
        ('rejected', 'Отклонено'),
        ('expired', 'Истекло'),
        ('cancelled', 'Отменено'),
    ]
    
    # Связь с документом (GenericForeignKey)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Рабочий процесс
    workflow = models.ForeignKey(
        SignatureWorkflow, 
        on_delete=models.CASCADE, 
        verbose_name="Рабочий процесс",
        related_name='signatures'
    )
    
    # Тип подписи и статус
    signature_type = models.CharField("Тип подписи", max_length=20, choices=SIGNATURE_TYPES)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Кто должен подписать и кто фактически подписал
    required_signer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='required_signatures',
        verbose_name="Требуемый подписант"
    )
    actual_signer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='actual_signatures',
        verbose_name="Фактический подписант"
    )
    
    # Данные подписи
    signature_notes = models.TextField("Комментарии к подписи", blank=True)
    signature_hash = models.CharField("Хеш подписи", max_length=128, blank=True)
    
    # Комментарии и причины
    notes = models.TextField("Комментарии", blank=True)
    rejection_reason = models.TextField("Причина отклонения", blank=True)
    cancellation_reason = models.TextField("Причина отмены", blank=True)
    
    # Временные метки
    required_by = models.DateTimeField("Требуется к", null=True, blank=True)
    signed_at = models.DateTimeField("Подписано в", null=True, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    
    class Meta:
        verbose_name = "Подпись документа"
        verbose_name_plural = "Подписи документов"
        unique_together = ['content_type', 'object_id', 'signature_type']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status']),
            models.Index(fields=['required_signer']),
            models.Index(fields=['workflow']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_signature_type_display()} - {self.content_object} ({self.get_status_display()})"
    
    @property
    def is_signed(self):
        """Проверяет, подписан ли документ"""
        return self.status == 'signed'
    
    @property
    def is_expired(self):
        """Проверяет, истек ли срок подписи"""
        if not self.required_by:
            return False
        return timezone.now() > self.required_by
    
    @property
    def can_be_signed(self):
        """Проверяет, можно ли подписать документ"""
        return self.status == 'pending' and not self.is_expired
    
    def can_sign(self, user):
        """Проверяет, может ли пользователь подписать документ"""
        if not self.can_be_signed:
            return False
        
        # Проверяем права пользователя в зависимости от типа подписи
        if self.signature_type == 'doctor':
            # Врач может подписать свой результат
            return user == self.required_signer
        elif self.signature_type == 'head_of_department':
            # Заведующий отделением может подписать
            return user.has_perm('document_signatures.can_sign_as_head')
        elif self.signature_type == 'chief_physician':
            # Главный врач может подписать
            return user.has_perm('document_signatures.can_sign_as_chief')
        elif self.signature_type == 'patient':
            # Пациент может подписать свой результат
            return user == self.required_signer
        elif self.signature_type == 'nurse':
            # Медсестра может подписать
            return user.has_perm('document_signatures.can_sign_as_nurse')
        elif self.signature_type == 'technician':
            # Техник может подписать
            return user.has_perm('document_signatures.can_sign_as_technician')
        elif self.signature_type == 'consultant':
            # Консультант может подписать
            return user.has_perm('document_signatures.can_sign_as_consultant')
        
        return False
    
    def sign(self, user, notes=''):
        """Подписывает документ"""
        if not self.can_sign(user):
            raise PermissionError("Пользователь не может подписать этот документ")
        
        self.actual_signer = user
        self.status = 'signed'
        self.signed_at = timezone.now()
        self.signature_notes = notes
        self.signature_hash = self._generate_signature_hash()
        
        self.save()
        
        # Отправляем сигнал о подписании
        from .signals import document_signed
        document_signed.send(sender=self.__class__, instance=self)
    
    def reject(self, user, reason):
        """Отклоняет документ"""
        if not user.has_perm('document_signatures.can_reject_signature'):
            raise PermissionError("Пользователь не может отклонять подписи")
        
        self.status = 'rejected'
        self.rejection_reason = reason
        self.actual_signer = user
        self.signed_at = timezone.now()
        self.save()
    
    def cancel(self, user, reason):
        """Отменяет подпись"""
        if not user.has_perm('document_signatures.can_cancel_signature'):
            raise PermissionError("Пользователь не может отменять подписи")
        
        self.status = 'cancelled'
        self.cancellation_reason = reason
        self.actual_signer = user
        self.signed_at = timezone.now()
        self.save()
    
    def _generate_signature_hash(self):
        """Генерирует хеш подписи для безопасности"""
        data = f"{self.content_type_id}:{self.object_id}:{self.signature_type}:{self.actual_signer_id}:{self.signed_at.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()


class SignatureTemplate(models.Model):
    """
    Шаблоны для быстрого создания подписей
    """
    name = models.CharField("Название", max_length=100)
    description = models.TextField("Описание", blank=True)
    
    # Настройки шаблона
    workflow = models.ForeignKey(
        SignatureWorkflow, 
        on_delete=models.CASCADE, 
        verbose_name="Рабочий процесс"
    )
    
    # Применяется к определенным типам документов
    content_types = models.ManyToManyField(
        ContentType, 
        verbose_name="Типы документов",
        help_text="К каким типам документов применяется этот шаблон"
    )
    
    # Автоматическое применение
    auto_apply = models.BooleanField("Автоматически применять", default=False)
    
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    
    class Meta:
        verbose_name = "Шаблон подписи"
        verbose_name_plural = "Шаблоны подписей"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def can_apply_to(self, document):
        """Проверяет, можно ли применить шаблон к документу"""
        content_type = ContentType.objects.get_for_model(document)
        return self.content_types.filter(pk=content_type.pk).exists()
