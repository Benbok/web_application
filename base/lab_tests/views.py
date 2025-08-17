from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages

from treatment_assignments.models import LabTestAssignment
from .models import LabTestResult
from .forms import build_lab_test_result_form

class LabTestAssignmentListView(LoginRequiredMixin, ListView):
    model = LabTestAssignment
    template_name = 'lab_tests/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')
        
        if query:
            # Нормализуем поисковый запрос
            query = query.strip().lower()
            queryset = queryset.filter(
                Q(patient__first_name__icontains=query) |
                Q(patient__last_name__icontains=query) |
                Q(patient__middle_name__icontains=query) |
                Q(lab_test__name__icontains=query) |
                # Дополнительный поиск в верхнем регистре
                Q(patient__first_name__icontains=query.capitalize()) |
                Q(patient__last_name__icontains=query.capitalize()) |
                Q(patient__middle_name__icontains=query.capitalize())
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

class LabTestResultCreateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        assignment = get_object_or_404(LabTestAssignment, pk=pk)
        procedure_definition = assignment.lab_test
        form = build_lab_test_result_form(procedure_definition.schema, user=request.user)
        return render(request, 'lab_tests/result_form.html', {
            'form': form,
            'assignment': assignment,
            'procedure_definition': procedure_definition
        })

    def post(self, request, pk):
        assignment = get_object_or_404(LabTestAssignment, pk=pk)
        procedure_definition = assignment.lab_test
        DynamicFormClass = build_lab_test_result_form(procedure_definition.schema, user=request.user)
        form = DynamicFormClass(request.POST)
        
        if form.is_valid():
            result = LabTestResult(
                lab_test_assignment=assignment,
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

            return redirect(reverse_lazy('lab_tests:assignment_list'))
        
        return render(request, 'lab_tests/result_form.html', {
            'form': form,
            'assignment': assignment,
            'procedure_definition': procedure_definition
        })

class LabTestResultDetailView(LoginRequiredMixin, DetailView):
    model = LabTestResult
    template_name = 'lab_tests/result_detail.html'
    context_object_name = 'result'

    def get_queryset(self):
        queryset = super().get_queryset()
        # Дополнительная фильтрация, если нужно
        return queryset

class LabTestResultUpdateView(LoginRequiredMixin, View):
    template_name = 'lab_tests/result_form.html'

    def get(self, request, pk):
        result = get_object_or_404(LabTestResult, pk=pk)
        initial_data = {'datetime_result': result.datetime_result, **result.data}
        form = build_lab_test_result_form(result.procedure_definition.schema, user=request.user, initial=initial_data)
        return render(request, self.template_name, {
            'form': form,
            'assignment': result.lab_test_assignment,
            'procedure_definition': result.procedure_definition,
            'result': result
        })

    def post(self, request, pk):
        result = get_object_or_404(LabTestResult, pk=pk)
        DynamicFormClass = build_lab_test_result_form(result.procedure_definition.schema, user=request.user)
        form = DynamicFormClass(request.POST)

        if form.is_valid():
            result.datetime_result = form.cleaned_data['datetime_result']
            result.data = {k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            result.author = request.user
            result.save()
            return redirect(reverse_lazy('lab_tests:result_detail', kwargs={'pk': result.pk}))

        return render(request, self.template_name, {
            'form': form,
            'assignment': result.lab_test_assignment,
            'procedure_definition': result.procedure_definition,
            'result': result
        })

class LabTestAssignmentRejectView(LoginRequiredMixin, View):
    """
    Представление для браковки лабораторного исследования
    """
    template_name = 'lab_tests/assignment_reject.html'
    
    def get(self, request, pk):
        assignment = get_object_or_404(LabTestAssignment, pk=pk)
        
        # Проверяем, можно ли забраковать назначение
        if not assignment.can_be_rejected():
            messages.error(request, 'Это назначение нельзя забраковать.')
            return redirect('lab_tests:assignment_list')
        
        return render(request, self.template_name, {
            'assignment': assignment,
            'title': 'Забраковать лабораторное исследование'
        })
    
    def post(self, request, pk):
        assignment = get_object_or_404(LabTestAssignment, pk=pk)
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, 'Необходимо указать причину брака.')
            return render(request, self.template_name, {
                'assignment': assignment,
                'title': 'Забраковать лабораторное исследование'
            })
        
        # Проверяем, можно ли забраковать назначение
        if not assignment.can_be_rejected():
            messages.error(request, 'Это назначение нельзя забраковать.')
            return redirect('lab_tests:assignment_list')
        
        try:
            # Бракуем назначение
            assignment.reject(rejection_reason, request.user)
            messages.success(request, 'Лабораторное исследование успешно забраковано.')
        except Exception as e:
            messages.error(request, f'Ошибка при браковке: {str(e)}')
        
        return redirect('lab_tests:assignment_list')