from django.http import JsonResponse
from django.views import View
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Diagnosis


class DiagnosisAjaxSearchView(LoginRequiredMixin, View):
    """
    AJAX view для поиска диагнозов по запросу.
    Возвращает результаты в формате, совместимом с Select2.
    """
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        page_size = 20
        
        if not query or len(query) < 2:
            return JsonResponse({
                'results': [],
                'pagination': {'more': False}
            })
        
        # Поиск по коду или названию диагноза
        queryset = Diagnosis.objects.filter(
            Q(code__icontains=query) | 
            Q(name__icontains=query)
        ).order_by('code', 'name')
        
        # Пагинация
        start = (page - 1) * page_size
        end = start + page_size
        diagnoses = queryset[start:end]
        
        results = []
        for diagnosis in diagnoses:
            results.append({
                'id': diagnosis.id,
                'text': f"{diagnosis.code} - {diagnosis.name}",
                'code': diagnosis.code,
                'name': diagnosis.name
            })
        
        return JsonResponse({
            'results': results,
            'pagination': {
                'more': queryset.count() > end
            }
        })


class DiagnosisAjaxSearchLightView(LoginRequiredMixin, View):
    """
    Облегченная версия AJAX поиска диагнозов.
    Возвращает только первые 50 результатов для быстрого старта.
    """
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        
        if not query:
            # Если запрос пустой, возвращаем популярные диагнозы
            diagnoses = Diagnosis.objects.filter(
                Q(code__startswith='J') |  # Респираторные заболевания
                Q(code__startswith='I') |  # Сердечно-сосудистые
                Q(code__startswith='K')    # Пищеварительные
            ).order_by('code')[:50]
        else:
            # Поиск по запросу
            diagnoses = Diagnosis.objects.filter(
                Q(code__icontains=query) | 
                Q(name__icontains=query)
            ).order_by('code', 'name')[:50]
        
        results = []
        for diagnosis in diagnoses:
            results.append({
                'id': diagnosis.id,
                'text': f"{diagnosis.code} - {diagnosis.name}",
                'code': diagnosis.code,
                'name': diagnosis.name
            })
        
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        }) 