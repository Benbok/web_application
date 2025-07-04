
from django.shortcuts import render
from django.views.generic import ListView
from django.http import JsonResponse
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
