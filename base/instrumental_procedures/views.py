from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q

from treatment_assignments.models import InstrumentalProcedureAssignment
from .models import InstrumentalProcedureResult, InstrumentalProcedureResultType
from .forms import build_instrumental_procedure_result_form

class InstrumentalProcedureAssignmentListView(LoginRequiredMixin, ListView):
    model = InstrumentalProcedureAssignment
    template_name = 'instrumental_procedures/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=query) |
                Q(patient__last_name__icontains=query) |
                Q(instrumental_procedure__name__icontains=query)
            )
        return queryset

class InstrumentalProcedureResultCreateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        assignment = get_object_or_404(InstrumentalProcedureAssignment, pk=pk)
        result_type_pk = request.GET.get('result_type_pk')

        if result_type_pk:
            # Шаг 2: Тип результата выбран, показываем форму
            result_type = get_object_or_404(InstrumentalProcedureResultType, pk=result_type_pk)
            form = build_instrumental_procedure_result_form(result_type.schema, result_type=result_type, user=request.user)
            return render(request, 'instrumental_procedures/result_form.html', {
                'form': form,
                'assignment': assignment,
                'result_type': result_type,
                'result_type_pk': result_type_pk # Передаем PK для скрытого поля
            })
        else:
            # Шаг 1: Тип результата не выбран, показываем список типов
            result_types = InstrumentalProcedureResultType.objects.all()
            query = request.GET.get('q')
            if query:
                result_types = result_types.filter(Q(name__icontains=query))
            
            return render(request, 'instrumental_procedures/select_result_type.html', {
                'assignment': assignment,
                'result_types': result_types,
                'query': query
            })

    def post(self, request, pk):
        assignment = get_object_or_404(InstrumentalProcedureAssignment, pk=pk)
        result_type_pk = request.POST.get('result_type_pk')

        if not result_type_pk:
            # Если result_type_pk отсутствует, это ошибка или попытка обойти выбор типа
            return redirect(reverse_lazy('instrumental_procedures:add_result', kwargs={'pk': pk}))

        result_type = get_object_or_404(InstrumentalProcedureResultType, pk=result_type_pk)
        DynamicFormClass = build_instrumental_procedure_result_form(result_type.schema, result_type=result_type, user=request.user)
        form = DynamicFormClass(request.POST)
        
        if form.is_valid():
            result = InstrumentalProcedureResult(
                instrumental_procedure_assignment=assignment,
                result_type=result_type,
                author=request.user,
                datetime_result=form.cleaned_data['datetime_result'],
                data={k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            )
            result.save()

            # Обновляем статус назначения
            assignment.status = 'completed'
            assignment.end_date = form.cleaned_data['datetime_result'] # Устанавливаем дату завершения
            assignment.save()

            return redirect(reverse_lazy('instrumental_procedures:assignment_list'))
        
        return render(request, 'instrumental_procedures/result_form.html', {
            'form': form,
            'assignment': assignment,
            'result_type': result_type,
            'result_type_pk': result_type_pk
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
        form = build_instrumental_procedure_result_form(result.result_type.schema, result_type=result.result_type, user=request.user, initial=initial_data)
        return render(request, self.template_name, {
            'form': form,
            'assignment': result.instrumental_procedure_assignment,
            'result_type': result.result_type,
            'result': result
        })

    def post(self, request, pk):
        result = get_object_or_404(InstrumentalProcedureResult, pk=pk)
        DynamicFormClass = build_instrumental_procedure_result_form(result.result_type.schema, result_type=result.result_type, user=request.user)
        form = DynamicFormClass(request.POST)

        if form.is_valid():
            result.datetime_result = form.cleaned_data['datetime_result']
            result.data = {k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            result.author = request.user
            result.save()
            return redirect(reverse_lazy('instrumental_procedures:result_detail', kwargs={'pk': result.pk}))

        return render(request, self.template_name, {
            'form': form,
            'assignment': result.instrumental_procedure_assignment,
            'result_type': result.result_type,
            'result': result
        })

class InstrumentalProcedureResultDeleteView(LoginRequiredMixin, DeleteView):
    model = InstrumentalProcedureResult
    template_name = 'instrumental_procedures/result_confirm_delete.html'
    context_object_name = 'result'
    success_url = reverse_lazy('instrumental_procedures:assignment_list')