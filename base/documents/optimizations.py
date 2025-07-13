"""
Оптимизации для модуля Documents
"""
import json
from functools import lru_cache
from django.core.cache import cache
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class DocumentOptimizations:
    """Класс для оптимизаций модуля Documents"""
    
    # Кэш для динамических форм
    FORM_CACHE_PREFIX = "document_form_"
    CACHE_TIMEOUT = 3600  # 1 час
    
    @classmethod
    @lru_cache(maxsize=128)
    def get_cached_form(cls, schema_hash, document_type_id, user_id):
        """
        Кэшированное получение динамической формы
        """
        cache_key = f"{cls.FORM_CACHE_PREFIX}{schema_hash}_{document_type_id}_{user_id}"
        cached_form = cache.get(cache_key)
        
        if cached_form is None:
            # Создаем форму и кэшируем
            from .forms import build_document_form
            from .models import DocumentType
            
            document_type = DocumentType.objects.get(id=document_type_id)
            cached_form = build_document_form(document_type.schema, document_type)
            cache.set(cache_key, cached_form, cls.CACHE_TIMEOUT)
        
        return cached_form
    
    @classmethod
    def invalidate_form_cache(cls, document_type_id):
        """
        Инвалидация кэша форм при изменении схемы
        """
        pattern = f"{cls.FORM_CACHE_PREFIX}*_{document_type_id}_*"
        cache.delete_pattern(pattern)


class DocumentQuerySet(models.QuerySet):
    """
    Оптимизированный QuerySet для документов
    """
    
    def with_related_data(self):
        """
        Предзагружает связанные данные для избежания N+1 запросов
        """
        return self.select_related(
            'document_type',
            'document_type__department',
            'author',
            'content_type'
        ).prefetch_related(
            'document_type__templates'
        )
    
    def by_department(self, department):
        """
        Фильтрация по отделению с оптимизацией
        """
        return self.filter(document_type__department=department)
    
    def by_author(self, author):
        """
        Фильтрация по автору
        """
        return self.filter(author=author)
    
    def search_in_data(self, query):
        """
        Поиск в JSON-данных (для PostgreSQL)
        """
        if hasattr(self.model, 'data_search'):
            return self.filter(data_search=query)
        return self.filter(data__icontains=query)


class DocumentIndexes:
    """
    Индексы для оптимизации запросов
    """
    
    class Meta:
        indexes = [
            # Индекс для поиска по типу документа
            models.Index(fields=['document_type']),
            
            # Индекс для поиска по автору
            models.Index(fields=['author']),
            
            # Индекс для поиска по дате
            models.Index(fields=['datetime_document']),
            
            # Индекс для поиска по статусу подписи
            models.Index(fields=['is_signed']),
            
            # GIN индекс для JSON-поля (PostgreSQL)
            GinIndex(fields=['data'], name='document_data_gin_idx'),
            
            # Составной индекс для частых запросов
            models.Index(
                fields=['document_type', 'datetime_document'],
                name='document_type_date_idx'
            ),
        ]


class DocumentSearch:
    """
    Система поиска документов
    """
    
    @staticmethod
    def create_search_vector(document):
        """
        Создает поисковый вектор для документа
        """
        search_data = {
            'title': document.document_type.name,
            'author': document.author.get_full_name() if document.author else '',
            'data': json.dumps(document.data, ensure_ascii=False),
            'position': document.author_position or '',
        }
        
        return ' '.join(str(v) for v in search_data.values() if v)
    
    @staticmethod
    def search_documents(query, queryset=None):
        """
        Поиск документов по тексту
        """
        from .models import ClinicalDocument
        
        if queryset is None:
            queryset = ClinicalDocument.objects.all()
        
        # Простой поиск по JSON-полю
        return queryset.filter(data__icontains=query) 