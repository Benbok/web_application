from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class SoftDeleteMixin(models.Model):
    """
    Миксин для реализации мягкого удаления назначений.
    
    Вместо физического удаления записи, назначается статус 'cancelled'
    и сохраняется информация об отмене (кто, когда, почему).
    """
    
    # Статусы назначения
    STATUS_CHOICES = [
        ('active', _('Активно')),
        ('completed', _('Завершено')),
        ('cancelled', _('Отменено')),
        ('paused', _('Приостановлено')),
        ('rejected', _('Забраковано')),
    ]
    
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    # Поля для отмены
    cancelled_at = models.DateTimeField(
        _('Дата отмены'),
        null=True,
        blank=True
    )
    
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Отменил'),
        related_name='%(class)s_cancelled'
    )
    
    cancellation_reason = models.TextField(
        _('Причина отмены'),
        blank=True,
        help_text=_('Укажите причину отмены назначения')
    )
    
    # Поля для приостановки
    paused_at = models.DateTimeField(
        _('Дата приостановки'),
        null=True,
        blank=True
    )
    
    paused_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Приостановил'),
        related_name='%(class)s_paused'
    )
    
    pause_reason = models.TextField(
        _('Причина приостановки'),
        blank=True,
        help_text=_('Укажите причину приостановки назначения')
    )
    
    # Поля для завершения
    completed_at = models.DateTimeField(
        _('Дата завершения'),
        null=True,
        blank=True
    )
    
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Завершил'),
        related_name='%(class)s_completed'
    )
    
    completion_notes = models.TextField(
        _('Примечания к завершению'),
        blank=True
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['cancelled_at']),
            models.Index(fields=['paused_at']),
            models.Index(fields=['completed_at']),
        ]
    
    def cancel(self, reason='', cancelled_by=None):
        """
        Отменяет назначение (мягкое удаление)
        
        Args:
            reason (str): Причина отмены
            cancelled_by (User): Пользователь, отменивший назначение
        """
        if self.status == 'cancelled':
            raise ValueError(_('Назначение уже отменено'))
        
        if self.status == 'completed':
            raise ValueError(_('Нельзя отменить завершенное назначение'))
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        
        # Если назначение было приостановлено, сбрасываем информацию о приостановке
        if self.status == 'paused':
            self.paused_at = None
            self.paused_by = None
            self.pause_reason = ''
        
        self.save(update_fields=[
            'status', 'cancelled_at', 'cancelled_by', 'cancellation_reason',
            'paused_at', 'paused_by', 'pause_reason'
        ])
    
    def pause(self, reason='', paused_by=None):
        """
        Приостанавливает назначение
        
        Args:
            reason (str): Причина приостановки
            paused_by (User): Пользователь, приостановивший назначение
        """
        if self.status not in ['active']:
            raise ValueError(_('Можно приостановить только активное назначение'))
        
        self.status = 'paused'
        self.paused_at = timezone.now()
        self.paused_by = paused_by
        self.pause_reason = reason
        
        self.save(update_fields=[
            'status', 'paused_at', 'paused_by', 'pause_reason'
        ])
    
    def resume(self):
        """
        Возобновляет приостановленное назначение
        """
        if self.status != 'paused':
            raise ValueError(_('Можно возобновить только приостановленное назначение'))
        
        self.status = 'active'
        self.paused_at = None
        self.paused_by = None
        self.pause_reason = ''
        
        self.save(update_fields=[
            'status', 'paused_at', 'paused_by', 'pause_reason'
        ])
    
    def complete(self, notes='', completed_by=None):
        """
        Завершает назначение
        
        Args:
            notes (str): Примечания к завершению
            completed_by (User): Пользователь, завершивший назначение
        """
        if self.status not in ['active', 'paused']:
            raise ValueError(_('Можно завершить только активное или приостановленное назначение'))
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.completed_by = completed_by
        self.completion_notes = notes
        
        # Сбрасываем информацию о приостановке
        if self.status == 'paused':
            self.paused_at = None
            self.paused_by = None
            self.pause_reason = ''
        
        self.save(update_fields=[
            'status', 'completed_at', 'completed_by', 'completion_notes',
            'paused_at', 'paused_by', 'pause_reason'
        ])
    
    def is_active(self):
        """Проверяет, активно ли назначение"""
        return self.status == 'active'
    
    def is_cancelled(self):
        """Проверяет, отменено ли назначение"""
        return self.status == 'cancelled'
    
    def is_paused(self):
        """Проверяет, приостановлено ли назначение"""
        return self.status == 'paused'
    
    def is_completed(self):
        """Проверяет, завершено ли назначение"""
        return self.status == 'completed'
    
    def can_be_cancelled(self):
        """Проверяет, можно ли отменить назначение"""
        return self.status in ['active', 'paused']
    
    def can_be_paused(self):
        """Проверяет, можно ли приостановить назначение"""
        return self.status == 'active'
    
    def can_be_resumed(self):
        """Проверяет, можно ли возобновить назначение"""
        return self.status == 'paused'
    
    def can_be_completed(self):
        """Проверяет, можно ли завершить назначение"""
        return self.status in ['active', 'paused']
    
    def get_status_display_with_date(self):
        """Возвращает статус с датой изменения"""
        if self.status == 'cancelled' and self.cancelled_at:
            return f"{self.get_status_display()} {self.cancelled_at.strftime('%d.%m.%Y %H:%M')}"
        elif self.status == 'paused' and self.paused_at:
            return f"{self.get_status_display()} {self.paused_at.strftime('%d.%m.%Y %H:%M')}"
        elif self.status == 'completed' and self.completed_at:
            return f"{self.get_status_display()} {self.completed_at.strftime('%d.%m.%Y %H:%M')}"
        else:
            return self.get_status_display()
    
    def get_status_history(self):
        """Возвращает историю изменений статуса"""
        history = []
        
        if self.cancelled_at:
            history.append({
                'status': 'cancelled',
                'date': self.cancelled_at,
                'user': self.cancelled_by,
                'reason': self.cancellation_reason
            })
        
        if self.paused_at:
            history.append({
                'status': 'paused',
                'date': self.paused_at,
                'user': self.paused_by,
                'reason': self.pause_reason
            })
        
        if self.completed_at:
            history.append({
                'status': 'completed',
                'date': self.completed_at,
                'user': self.completed_by,
                'notes': self.completion_notes
            })
        
        # Сортируем по дате (новые сначала)
        history.sort(key=lambda x: x['date'], reverse=True)
        return history 