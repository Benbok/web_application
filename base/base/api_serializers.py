from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from .models import ArchiveLog, ArchiveConfiguration


class ContentTypeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ContentType
    """
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'name']


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для пользователей
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ArchiveLogSerializer(serializers.ModelSerializer):
    """
    Сериализатор для логов архивирования
    """
    content_type = ContentTypeSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = ArchiveLog
        fields = [
            'id', 'content_type', 'object_id', 'action', 'action_display',
            'user', 'timestamp', 'reason', 'ip_address', 'user_agent',
            'previous_data', 'new_data'
        ]
        read_only_fields = [
            'id', 'content_type', 'object_id', 'action', 'action_display',
            'user', 'timestamp', 'ip_address', 'user_agent',
            'previous_data', 'new_data'
        ]


class ArchiveConfigurationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для конфигурации архивирования
    """
    content_type = ContentTypeSerializer(read_only=True)
    model_name = serializers.CharField(source='content_type.model', read_only=True)
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    
    class Meta:
        model = ArchiveConfiguration
        fields = [
            'id', 'content_type', 'model_name', 'app_label',
            'is_archivable', 'cascade_archive', 'cascade_restore',
            'auto_archive_related', 'archive_after_days',
            'show_archived_in_list', 'show_archived_in_search',
            'allow_restore', 'require_reason',
            'archive_permission', 'restore_permission'
        ]


class ArchiveActionSerializer(serializers.Serializer):
    """
    Сериализатор для действий архивирования
    """
    action = serializers.ChoiceField(
        choices=[('archive', 'Архивирование'), ('restore', 'Восстановление')],
        help_text="Тип действия: архивирование или восстановление"
    )
    reason = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Причина архивирования (необязательно для восстановления)"
    )
    cascade = serializers.BooleanField(
        default=True,
        help_text="Выполнять каскадное архивирование/восстановление"
    )
    record_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Список ID записей для массового архивирования"
    )


class ArchiveStatusSerializer(serializers.Serializer):
    """
    Сериализатор для статуса архивирования
    """
    is_archived = serializers.BooleanField(help_text="Статус архивирования")
    archived_at = serializers.DateTimeField(
        allow_null=True,
        help_text="Дата и время архивирования"
    )
    archived_by = UserSerializer(
        allow_null=True,
        help_text="Пользователь, выполнивший архивирование"
    )
    archive_reason = serializers.CharField(
        allow_blank=True,
        help_text="Причина архивирования"
    )


class BulkArchiveResponseSerializer(serializers.Serializer):
    """
    Сериализатор для ответа массового архивирования
    """
    success = serializers.BooleanField(help_text="Успешность операции")
    archived_count = serializers.IntegerField(help_text="Количество архивированных записей")
    errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="Список ошибок"
    )
    message = serializers.CharField(help_text="Сообщение о результате")


class ArchiveFilterSerializer(serializers.Serializer):
    """
    Сериализатор для фильтров архивирования
    """
    STATUS_CHOICES = [
        ('', 'Все записи'),
        ('active', 'Активные'),
        ('archived', 'Архивированные'),
    ]
    
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        allow_blank=True,
        help_text="Статус записей"
    )
    archive_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Поиск по причине архивирования"
    )
    archived_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Пользователь, выполнивший архивирование"
    )
    archived_since = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Архивировано с даты"
    )
    archived_until = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Архивировано до даты"
    )
    page = serializers.IntegerField(
        required=False,
        min_value=1,
        default=1,
        help_text="Номер страницы"
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        default=20,
        help_text="Размер страницы"
    )
