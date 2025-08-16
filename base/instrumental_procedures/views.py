from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages

from treatment_assignments.models import InstrumentalProcedureAssignment
from .models import InstrumentalProcedureResult
from .forms import build_instrumental_procedure_result_form

class InstrumentalProcedureAssignmentListView(LoginRequiredMixin, ListView):
    model = InstrumentalProcedureAssignment
    template_name = 'instrumental_procedures/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')
        
        if query:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=query) |
                Q(patient__last_name__icontains=query) |
                Q(instrumental_procedure__name__icontains=query)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

class InstrumentalProcedureResultCreateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        assignment = get_object_or_404(InstrumentalProcedureAssignment, pk=pk)
        procedure_definition = assignment.instrumental_procedure
        form = build_instrumental_procedure_result_form(procedure_definition.schema, user=request.user)
        return render(request, 'instrumental_procedures/result_form.html', {
            'form': form,
            'assignment': assignment,
            'procedure_definition': procedure_definition
        })

    def post(self, request, pk):
        assignment = get_object_or_404(InstrumentalProcedureAssignment, pk=pk)
        procedure_definition = assignment.instrumental_procedure
        DynamicFormClass = build_instrumental_procedure_result_form(procedure_definition.schema, user=request.user)
        form = DynamicFormClass(request.POST)
        
        if form.is_valid():
            result = InstrumentalProcedureResult(
                instrumental_procedure_assignment=assignment,
                procedure_definition=procedure_definition,
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
            'procedure_definition': procedure_definition
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
            'assignment': result.instrumental_procedure_assignment,
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
            result.save()
            return redirect(reverse_lazy('instrumental_procedures:result_detail', kwargs={'pk': result.pk}))

        return render(request, self.template_name, {
            'form': form,
            'assignment': result.instrumental_procedure_assignment,
            'procedure_definition': result.procedure_definition,
            'result': result
        })

class InstrumentalProcedureAssignmentRejectView(LoginRequiredMixin, View):
    """
    Представление для браковки инструментального исследования
    """
    template_name = 'instrumental_procedures/assignment_reject.html'
    
    def get(self, request, pk):
        assignment = get_object_or_404(InstrumentalProcedureAssignment, pk=pk)
        
        # Проверяем, можно ли забраковать назначение
        if not assignment.can_be_rejected():
            messages.error(request, 'Это назначение нельзя забраковать.')
            return redirect('instrumental_procedures:assignment_list')
        
        return render(request, self.template_name, {
            'assignment': assignment,
            'title': 'Забраковать инструментальное исследование'
        })
    
    def post(self, request, pk):
        assignment = get_object_or_404(InstrumentalProcedureAssignment, pk=pk)
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, 'Необходимо указать причину брака.')
            return render(request, self.template_name, {
                'assignment': assignment,
                'title': 'Забраковать инструментальное исследование'
            })
        
        # Проверяем, можно ли забраковать назначение
        if not assignment.can_be_rejected():
            messages.error(request, 'Это назначение нельзя забраковать.')
            return redirect('instrumental_procedures:assignment_list')
        
        try:
            # Бракуем назначение
            assignment.reject(rejection_reason, request.user)
            messages.success(request, 'Инструментальное исследование успешно забраковано.')
        except Exception as e:
            messages.error(request, f'Ошибка при браковке: {str(e)}')
        
        return redirect('instrumental_procedures:assignment_list')