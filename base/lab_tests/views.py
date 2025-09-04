from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages

# Импорт treatment_assignments удален - больше не нужен
from .models import LabTestResult
from .forms import build_lab_test_result_form
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from document_signatures.services import SignatureService


class LabTestResultListView(LoginRequiredMixin, ListView):
    model = LabTestResult
    template_name = 'lab_tests/result_list.html'
    context_object_name = 'results'
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
                Q(procedure_definition__name__icontains=query) |
                # Дополнительный поиск в верхнем регистре
                Q(patient__first_name__icontains=query.capitalize()) |
                Q(patient__last_name__icontains=query.capitalize()) |
                Q(patient__middle_name__icontains=query.capitalize())
            )
        
        # Фильтрация по статусу
        if status:
            if status == 'completed':
                queryset = queryset.filter(is_completed=True)
            elif status == 'active':
                queryset = queryset.filter(status='active')
            elif status == 'cancelled':
                queryset = queryset.filter(status='cancelled')
        
        return queryset

class LabTestResultCreateView(LoginRequiredMixin, View):
    def get(self, request):
        # Получаем список доступных тестов для создания результата
        from .models import LabTestDefinition
        tests = LabTestDefinition.objects.all()
        return render(request, 'lab_tests/result_create.html', {
            'tests': tests
        })

    def post(self, request):
        test_id = request.POST.get('procedure_definition')
        patient_id = request.POST.get('patient')
        
        if not test_id or not patient_id:
            messages.error(request, 'Необходимо выбрать тест и пациента')
            return redirect('lab_tests:result_create')
        
        from .models import LabTestDefinition
        from patients.models import Patient
        
        procedure_definition = get_object_or_404(LabTestDefinition, pk=test_id)
        patient = get_object_or_404(Patient, pk=patient_id)
        
        DynamicFormClass = build_lab_test_result_form(procedure_definition.schema, user=request.user)
        form = DynamicFormClass(request.POST)
        
        if form.is_valid():
            result = LabTestResult(
                patient=patient,
                procedure_definition=procedure_definition,
                author=request.user,
                datetime_result=form.cleaned_data['datetime_result'],
                data={k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            )
            result.save()

            messages.success(request, 'Результат успешно создан')
            return redirect(reverse_lazy('lab_tests:result_list'))
        
        return render(request, 'lab_tests/result_form.html', {
            'form': form,
            'procedure_definition': procedure_definition,
            'patient': patient
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
            
            # Проверяем, есть ли данные в результате (не только datetime_result)
            data_fields = {k: v for k, v in form.cleaned_data.items() if k != 'datetime_result'}
            if data_fields and any(v for v in data_fields.values() if v):
                result.is_completed = True
                messages.success(request, 'Данные результата успешно заполнены')
            else:
                result.is_completed = False
                messages.warning(request, 'Результат обновлен, но данные не заполнены')
            
            result.save()
            return redirect(reverse_lazy('lab_tests:result_detail', kwargs={'pk': result.pk}))

        return render(request, self.template_name, {
            'form': form,
            'procedure_definition': result.procedure_definition,
            'result': result
        })

class LabTestResultDeleteView(LoginRequiredMixin, View):
    template_name = 'lab_tests/result_confirm_delete.html'

    def get(self, request, pk):
        result = get_object_or_404(LabTestResult, pk=pk)
        return render(request, self.template_name, { 'result': result })

    def post(self, request, pk):
        result = get_object_or_404(LabTestResult, pk=pk)
        try:
            result.delete()
            messages.success(request, 'Результат успешно удален.')
        except Exception as e:
            messages.error(request, f'Не удалось удалить результат: {e}')
        return redirect('lab_tests:result_list')


class LabTestResultSignView(LoginRequiredMixin, View):
    """
    View для подписания результата лабораторного исследования
    """
    
    def post(self, request, pk):
        result = get_object_or_404(LabTestResult, pk=pk)
        
        try:
            # Проверяем, что результат заполнен
            if not result.is_completed:
                messages.error(request, 'Нельзя подписать незаполненный результат')
                return redirect('lab_tests:result_detail', pk=pk)
            
            # Проверяем, что подписи еще не созданы
            from document_signatures.models import DocumentSignature
            existing_signatures = DocumentSignature.objects.filter(
                content_type__model='labtestresult',
                object_id=result.pk
            )
            
            if not existing_signatures.exists():
                # Создаем подписи для документа
                SignatureService.create_signatures_for_document(result, 'simple')
                messages.success(request, 'Подписи созданы для документа')
                # Обновляем поиск подписей после создания
                existing_signatures = DocumentSignature.objects.filter(
                    content_type__model='labtestresult',
                    object_id=result.pk
                )
            
            # Подписываем документ текущим пользователем
            signature = existing_signatures.filter(
                signature_type='doctor',
                status='pending'
            ).first()
            
            if signature:
                SignatureService.sign_document(signature.id, request.user)
                messages.success(request, 'Документ успешно подписан!')
            else:
                messages.warning(request, 'Нет доступных подписей для подписания')
            
        except Exception as e:
            messages.error(request, f'Ошибка при подписании: {str(e)}')
        
        return redirect('lab_tests:result_detail', pk=pk)


class LabTestRejectView(LoginRequiredMixin, View):
    """View для отклонения лабораторного исследования"""
    
    def get(self, request, pk):
        from .forms import LabTestRejectionForm
        result = get_object_or_404(LabTestResult, pk=pk)
        form = LabTestRejectionForm()
        
        context = {
            'result': result,
            'form': form,
            'action_type': 'reject',
            'action_title': 'Отклонить исследование',
            'submit_text': 'Отклонить',
        }
        return render(request, 'lab_tests/action_form.html', context)
    
    def post(self, request, pk):
        from .forms import LabTestRejectionForm
        result = get_object_or_404(LabTestResult, pk=pk)
        form = LabTestRejectionForm(request.POST)
        
        if form.is_valid():
            try:
                # Обновляем статус через сервис
                from examination_management.services import ExaminationStatusService
                
                # Находим связанное назначение через examination_plan или через поиск в examination_management
                if result.examination_plan:
                    # Если есть прямая связь с планом
                    examination_plan = result.examination_plan
                else:
                    # Ищем через patient и procedure_definition
                    from examination_management.models import ExaminationLabTest
                    examination_plan = ExaminationLabTest.objects.filter(
                        lab_test=result.procedure_definition,
                        examination_plan__encounter__patient=result.patient
                    ).first()
                
                if examination_plan:
                    ExaminationStatusService.update_assignment_status(
                        examination_plan, 'rejected', 
                        f"Отклонено: {form.cleaned_data['rejection_reason']} - {form.cleaned_data.get('rejection_notes', '')}"
                    )
                
                messages.success(request, 'Исследование успешно отклонено')
                return redirect('lab_tests:result_list')
                
            except Exception as e:
                messages.error(request, f'Ошибка при отклонении: {str(e)}')
        
        context = {
            'result': result,
            'form': form,
            'action_type': 'reject',
            'action_title': 'Отклонить исследование',
            'submit_text': 'Отклонить',
        }
        return render(request, 'lab_tests/action_form.html', context)


class LabTestDisqualifyView(LoginRequiredMixin, View):
    """View для забраковки лабораторного исследования"""
    
    def get(self, request, pk):
        from .forms import LabTestDisqualificationForm
        result = get_object_or_404(LabTestResult, pk=pk)
        form = LabTestDisqualificationForm()
        
        context = {
            'result': result,
            'form': form,
            'action_type': 'disqualify',
            'action_title': 'Забраковать исследование',
            'submit_text': 'Забраковать',
        }
        return render(request, 'lab_tests/action_form.html', context)
    
    def post(self, request, pk):
        from .forms import LabTestDisqualificationForm
        result = get_object_or_404(LabTestResult, pk=pk)
        form = LabTestDisqualificationForm(request.POST)
        
        if form.is_valid():
            try:
                # Обновляем статус через сервис
                from examination_management.services import ExaminationStatusService
                
                # Находим связанное назначение через examination_plan или через поиск в examination_management
                if result.examination_plan:
                    # Если есть прямая связь с планом
                    examination_plan = result.examination_plan
                else:
                    # Ищем через patient и procedure_definition
                    from examination_management.models import ExaminationLabTest
                    examination_plan = ExaminationLabTest.objects.filter(
                        lab_test=result.procedure_definition,
                        examination_plan__encounter__patient=result.patient
                    ).first()
                
                if examination_plan:
                    ExaminationStatusService.update_assignment_status(
                        examination_plan, 'rejected', 
                        f"Забраковано: {form.cleaned_data['disqualification_reason']} - {form.cleaned_data.get('disqualification_notes', '')}"
                    )
                
                messages.success(request, 'Исследование успешно забраковано')
                return redirect('lab_tests:result_list')
                
            except Exception as e:
                messages.error(request, f'Ошибка при забраковке: {str(e)}')
        
        context = {
            'result': result,
            'form': form,
            'action_type': 'disqualify',
            'action_title': 'Забраковать исследование',
            'submit_text': 'Забраковать',
        }
        return render(request, 'lab_tests/action_form.html', context)