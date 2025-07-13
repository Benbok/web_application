"""
Сервисный слой для модуля Documents
"""
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.utils import timezone
import json
import hashlib

from .models import DocumentType, ClinicalDocument, DocumentTemplate, DocumentVersion, DocumentAuditLog
from .optimizations import DocumentOptimizations


class DocumentService:
    """
    Сервис для работы с документами
    """
    
    @staticmethod
    def create_document(
        document_type: DocumentType,
        content_object: Any,
        author: AbstractUser,
        data: Dict[str, Any],
        datetime_document: Optional[timezone.datetime] = None,
        author_position: Optional[str] = None
    ) -> ClinicalDocument:
        """
        Создание нового документа с аудитом
        """
        with transaction.atomic():
            # Валидация данных против схемы
            document_type.validate_schema()
            
            # Создание документа
            document = ClinicalDocument.objects.create(
                document_type=document_type,
                content_object=content_object,
                author=author,
                author_position=author_position,
                datetime_document=datetime_document or timezone.now(),
                data=data
            )
            
            # Создание первой версии
            DocumentVersion.objects.create(
                document=document,
                version_number=1,
                data=data,
                author=author,
                change_description="Создание документа"
            )
            
            # Запись в аудит
            DocumentAuditLog.objects.create(
                document=document,
                action='created',
                user=author,
                changes={'data': data}
            )
            
            return document
    
    @staticmethod
    def update_document(
        document: ClinicalDocument,
        user: AbstractUser,
        data: Dict[str, Any],
        datetime_document: Optional[timezone.datetime] = None,
        change_description: str = ""
    ) -> ClinicalDocument:
        """
        Обновление документа с версионированием и аудитом
        """
        with transaction.atomic():
            # Сохраняем старые данные для аудита
            old_data = document.data.copy()
            
            # Обновляем документ
            if datetime_document:
                document.datetime_document = datetime_document
            document.data = data
            document.save()
            
            # Создаем новую версию
            next_version = document.versions.count() + 1
            DocumentVersion.objects.create(
                document=document,
                version_number=next_version,
                data=data,
                author=user,
                change_description=change_description or "Обновление документа"
            )
            
            # Запись в аудит
            DocumentAuditLog.objects.create(
                document=document,
                action='updated',
                user=user,
                changes={
                    'old_data': old_data,
                    'new_data': data,
                    'description': change_description
                }
            )
            
            return document
    
    @staticmethod
    def sign_document(document: ClinicalDocument, user: AbstractUser) -> ClinicalDocument:
        """
        Подписание документа
        """
        with transaction.atomic():
            document.is_signed = True
            document.save()
            
            DocumentAuditLog.objects.create(
                document=document,
                action='signed',
                user=user
            )
            
            return document
    
    @staticmethod
    def cancel_document(document: ClinicalDocument, user: AbstractUser, reason: str = "") -> ClinicalDocument:
        """
        Аннулирование документа
        """
        with transaction.atomic():
            document.is_canceled = True
            document.save()
            
            DocumentAuditLog.objects.create(
                document=document,
                action='canceled',
                user=user,
                changes={'reason': reason}
            )
            
            return document
    
    @staticmethod
    def archive_document(document: ClinicalDocument, user: AbstractUser) -> ClinicalDocument:
        """
        Архивирование документа
        """
        with transaction.atomic():
            document.is_archived = True
            document.save()
            
            DocumentAuditLog.objects.create(
                document=document,
                action='archived',
                user=user
            )
            
            return document


class DocumentTemplateService:
    """
    Сервис для работы с шаблонами документов
    """
    
    @staticmethod
    def create_template(
        name: str,
        document_type: DocumentType,
        template_data: Dict[str, Any],
        author: AbstractUser,
        is_global: bool = False,
        description: str = ""
    ) -> DocumentTemplate:
        """
        Создание нового шаблона
        """
        template = DocumentTemplate.objects.create(
            name=name,
            document_type=document_type,
            template_data=template_data,
            author=author,
            is_global=is_global,
            description=description
        )
        
        # Валидация данных шаблона
        template.validate_template_data()
        
        return template
    
    @staticmethod
    def apply_template(
        template: DocumentTemplate,
        base_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Применение шаблона к данным
        """
        result_data = base_data.copy() if base_data else {}
        result_data.update(template.template_data)
        
        # Увеличиваем счетчик использований
        template.increment_usage()
        
        return result_data
    
    @staticmethod
    def get_available_templates(
        document_type: DocumentType,
        user: AbstractUser
    ) -> List[DocumentTemplate]:
        """
        Получение доступных шаблонов для пользователя
        """
        queryset = DocumentTemplate.objects.filter(
            document_type=document_type,
            is_active=True
        )
        
        if user.is_superuser:
            return list(queryset)
        
        # Пользователь видит свои шаблоны и глобальные
        return list(queryset.filter(
            models.Q(is_global=True) | models.Q(author=user)
        ))


class DocumentSearchService:
    """
    Сервис для поиска документов
    """
    
    @staticmethod
    def search_documents(
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        user: Optional[AbstractUser] = None
    ) -> List[ClinicalDocument]:
        """
        Поиск документов с фильтрацией
        """
        queryset = ClinicalDocument.objects.with_related_data()
        
        # Применяем фильтры
        if filters:
            if 'document_type' in filters:
                queryset = queryset.filter(document_type=filters['document_type'])
            if 'author' in filters:
                queryset = queryset.filter(author=filters['author'])
            if 'date_from' in filters:
                queryset = queryset.filter(datetime_document__gte=filters['date_from'])
            if 'date_to' in filters:
                queryset = queryset.filter(datetime_document__lte=filters['date_to'])
            if 'is_signed' in filters:
                queryset = queryset.filter(is_signed=filters['is_signed'])
        
        # Ограничиваем доступ пользователя
        if user and not user.is_superuser:
            queryset = queryset.filter(author=user)
        
        # Выполняем поиск
        if query:
            queryset = queryset.search_in_data(query)
        
        return list(queryset)
    
    @staticmethod
    def get_document_statistics(
        user: Optional[AbstractUser] = None,
        date_from: Optional[timezone.datetime] = None,
        date_to: Optional[timezone.datetime] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики по документам
        """
        queryset = ClinicalDocument.objects.all()
        
        if user and not user.is_superuser:
            queryset = queryset.filter(author=user)
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        stats = {
            'total_documents': queryset.count(),
            'signed_documents': queryset.filter(is_signed=True).count(),
            'canceled_documents': queryset.filter(is_canceled=True).count(),
            'archived_documents': queryset.filter(is_archived=True).count(),
            'documents_by_type': {},
            'documents_by_month': {},
        }
        
        # Статистика по типам документов
        for doc_type in DocumentType.objects.all():
            count = queryset.filter(document_type=doc_type).count()
            if count > 0:
                stats['documents_by_type'][doc_type.name] = count
        
        return stats


class DocumentCacheService:
    """
    Сервис для работы с кэшем документов
    """
    
    CACHE_PREFIX = "document_cache_"
    CACHE_TIMEOUT = 3600  # 1 час
    
    @classmethod
    def get_cached_form(cls, document_type: DocumentType, user: AbstractUser):
        """
        Получение кэшированной формы
        """
        cache_key = f"{cls.CACHE_PREFIX}form_{document_type.id}_{user.id}_{document_type.schema_hash}"
        cached_form = cache.get(cache_key)
        
        if cached_form is None:
            from .forms import build_document_form
            cached_form = build_document_form(
                document_type.schema, 
                document_type=document_type, 
                user=user
            )
            cache.set(cache_key, cached_form, cls.CACHE_TIMEOUT)
        
        return cached_form
    
    @classmethod
    def invalidate_document_cache(cls, document_type_id: int):
        """
        Инвалидация кэша для типа документа
        """
        pattern = f"{cls.CACHE_PREFIX}form_{document_type_id}_*"
        cache.delete_pattern(pattern)
    
    @classmethod
    def get_cached_templates(cls, document_type: DocumentType, user: AbstractUser):
        """
        Получение кэшированных шаблонов
        """
        cache_key = f"{cls.CACHE_PREFIX}templates_{document_type.id}_{user.id}"
        cached_templates = cache.get(cache_key)
        
        if cached_templates is None:
            cached_templates = DocumentTemplateService.get_available_templates(document_type, user)
            cache.set(cache_key, cached_templates, cls.CACHE_TIMEOUT)
        
        return cached_templates 