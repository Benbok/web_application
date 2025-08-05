
from django.shortcuts import render
from django.views.generic import ListView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import Medication

class MedicationListView(ListView):
    model = Medication
    template_name = 'pharmacy/medication_list.html'
    context_object_name = 'medications'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Список препаратов'
        context['search_query'] = self.request.GET.get('q', '')
        return context


def medication_detail_api(request, pk):
    medication = Medication.objects.get(pk=pk)
    data = {
        'id': medication.pk,
        'name': medication.name,
        'default_dosage': medication.default_dosage,
        'default_frequency': medication.default_frequency,
        'default_duration': medication.default_duration,
        'unit': medication.unit,
        'form': medication.form,
        'description': medication.description,
        'default_dosage_per_kg': medication.default_dosage_per_kg,
        'default_dosage_per_kg_unit': medication.default_dosage_per_kg_unit,
        'default_frequency_hours_options': medication.default_frequency_hours_options,
        'default_route': medication.default_route,
    }
    return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class MedicationAjaxSearchView(View):
    """AJAX endpoint для поиска препаратов по МНН и торговым названиям"""
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        page = request.GET.get('page', 1)
        
        if not query or len(query) < 2:
            return JsonResponse({
                'results': [],
                'pagination': {'more': False}
            })
        
        from django.db.models import Q
        
        # Поиск по МНН и торговым названиям
        medications = Medication.objects.filter(
            Q(name__icontains=query) |  # Поиск по МНН
            Q(trade_names__name__icontains=query)  # Поиск по торговым названиям
        ).distinct().order_by('name')[:20]
        
        results = []
        for medication in medications:
            # Получаем торговые названия для этого препарата
            trade_names = medication.trade_names.filter(name__icontains=query)
            
            if trade_names.exists():
                # Если найдены торговые названия, показываем их
                for trade_name in trade_names:
                    results.append({
                        'id': medication.pk,
                        'text': f"{trade_name.name} ({medication.name})",
                        'trade_name_id': trade_name.pk,  # Добавляем ID торгового наименования
                        'trade_name': trade_name.name,   # Добавляем название торгового наименования
                    })
            else:
                # Если поиск был по МНН, показываем МНН
                results.append({
                    'id': medication.pk,
                    'text': f"{medication.name}",
                    'trade_name_id': None,  # Нет торгового наименования
                    'trade_name': None,
                })
        
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        })


@method_decorator(csrf_exempt, name='dispatch')
class MedicationAjaxSearchLightView(View):
    """Облегченный AJAX endpoint для поиска препаратов по МНН и торговым названиям"""
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        page = request.GET.get('page', 1)
        
        from django.db.models import Q
        
        if not query:
            # Возвращаем первые 50 препаратов с их торговыми названиями для быстрого старта
            medications = Medication.objects.all().order_by('name')[:50]
            results = []
            for medication in medications:
                # Показываем МНН и первое торговое название
                trade_names = medication.trade_names.all()[:1]
                if trade_names.exists():
                    results.append({
                        'id': medication.pk,
                        'text': f"{trade_names[0].name} ({medication.name})",
                    })
                else:
                    results.append({
                        'id': medication.pk,
                        'text': f"{medication.name}",
                    })
        else:
            # Поиск по МНН и торговым названиям
            medications = Medication.objects.filter(
                Q(name__icontains=query) |  # Поиск по МНН
                Q(trade_names__name__icontains=query)  # Поиск по торговым названиям
            ).distinct().order_by('name')[:20]
            
            results = []
            for medication in medications:
                # Получаем торговые названия для этого препарата
                trade_names = medication.trade_names.filter(name__icontains=query)
                
                if trade_names.exists():
                    # Если найдены торговые названия, показываем их
                    for trade_name in trade_names:
                        results.append({
                            'id': medication.pk,
                            'text': f"{trade_name.name} ({medication.name})",
                        })
                else:
                    # Если поиск был по МНН, показываем МНН
                    results.append({
                        'id': medication.pk,
                        'text': f"{medication.name}",
                    })
        
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        })
