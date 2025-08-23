from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages

# Импорт treatment_assignments удален - больше не нужен
from .models import InstrumentalProcedureResult
from .forms import build_instrumental_procedure_result_form

class InstrumentalProcedureResultListView(LoginRequiredMixin, ListView):
    model = InstrumentalProcedureResult
    template_name = 'instrumental_procedures/result_list.html'
    context_object_name = 'results'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        
        if query:
            # Нормализуем поисковый запрос
            query = query.strip().lower()
            queryset = queryset.filter(
                Q(patient__first_name__icontains=query) |
                Q(patient__last_name__icontains=query) |
                Q(patient__middle_name__icontains=query) |
                Q(procedure_definition__name__icontains=query) |
                # Дополнительный поиск в верхнем регистре
                Q(patient__first_name__icontains=query.capitalize()) |
                Q(patient__last_name__icontains=query.capitalize()) |
                Q(patient__middle_name__icontains=query.capitalize())
            )
        
        return queryset

class InstrumentalProcedureResultCreateView(LoginRequiredMixin, View):
    def get(self, request):
        # Получаем список доступных процедур для создания результата
        from .models import InstrumentalProcedureDefinition
        procedures = InstrumentalProcedureDefinition.objects.all()
        return render(request, 'instrumental_procedures/result_create.html', {
            'procedures': procedures
        })

    def post(self, request):
        procedure_id = request.POST.get('procedure_definition')
        patient_id = request.POST.get('patient')
        
        if not procedure_id or not patient_id:
            messages.error(request, 'Необходимо выбрать процедуру и пациента')
            return redirect('instrumental_procedures:result_create')
        
        from .models import InstrumentalProcedureDefinition
        from patients.models import Patient
        
        procedure_definition = get_object_or_404(InstrumentalProcedureDefinition, pk=procedure_id)
        patient = get_object_or_404(Patient, pk=patient_id)
        
        DynamicFormClass = build_instrumental_procedure_result_form(procedure_definition.schema, user=request.user)
        form = DynamicFormClass(request.POST)
        
        if form.is_valid():
            result = InstrumentalProcedureResult(
                patient=patient,
                procedure_definition=procedure_definition,
                author=request.user,
                datetime_result=form.cleaned_data['datetime_result'],
                data={k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            )
            result.save()

            messages.success(request, 'Результат успешно создан')
            return redirect(reverse_lazy('instrumental_procedures:result_list'))
        
        return render(request, 'instrumental_procedures/result_form.html', {
            'form': form,
            'procedure_definition': procedure_definition,
            'patient': patient
        })

class InstrumentalProcedureResultDetailView(LoginRequiredMixin, DetailView):
    model = InstrumentalProcedureResult
    template_name = 'instrumental_procedures/result_detail.html'
    context_object_name = 'result'

    def get_queryset(self):
        queryset = super().get_queryset()
        # Дополнительная фильтрация, если нужно
        return queryset

class InstrumentalProcedureResultUpdateView(LoginRequiredMixin, View):
    template_name = 'instrumental_procedures/result_form.html'

    def get(self, request, pk):
        result = get_object_or_404(InstrumentalProcedureResult, pk=pk)
        initial_data = {'datetime_result': result.datetime_result, **result.data}
        form = build_instrumental_procedure_result_form(result.procedure_definition.schema, user=request.user, initial=initial_data)
        return render(request, self.template_name, {
            'form': form,
            'procedure_definition': result.procedure_definition,
            'result': result
        })

    def post(self, request, pk):
        result = get_object_or_404(InstrumentalProcedureResult, pk=pk)
        DynamicFormClass = build_instrumental_procedure_result_form(result.procedure_definition.schema, user=request.user)
        form = DynamicFormClass(request.POST)

        if form.is_valid():
            result.datetime_result = form.cleaned_data['datetime_result']
            result.data = {k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            result.author = request.user
            
            # Проверяем, есть ли данные в результате (не только datetime_result)
            data_fields = {k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            if data_fields and any(v for v in data_fields.values() if v):
                result.is_completed = True
                messages.success(request, 'Данные результата успешно заполнены')
            else:
                result.is_completed = False
                messages.warning(request, 'Результат обновлен, но данные не заполнены')
            
            result.save()
            return redirect(reverse_lazy('instrumental_procedures:result_detail', kwargs={'pk': result.pk}))

        return render(request, self.template_name, {
            'form': form,
            'procedure_definition': result.procedure_definition,
            'result': result
        })