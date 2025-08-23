from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.views import View
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count
from django.utils import timezone

from .models import DocumentSignature, SignatureWorkflow, SignatureTemplate
from .services import SignatureService
from .forms import SignatureForm, SignatureWorkflowForm, SignatureTemplateForm


class SignatureListView(LoginRequiredMixin, ListView):
    """
    Список подписей для пользователя
    """
    model = DocumentSignature
    template_name = 'document_signatures/signature_list.html'
    context_object_name = 'signatures'
    paginate_by = 20
    
    def get_queryset(self):
        """Получаем подписи для текущего пользователя"""
        queryset = SignatureService.get_pending_signatures_for_user(self.request.user)
        
        # Фильтрация по типу подписи
        signature_type = self.request.GET.get('type')
        if signature_type:
            queryset = queryset.filter(signature_type=signature_type)
        
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Поиск по названию документа
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(content_type__model__icontains=search) |
                Q(content_type__app_label__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Статистика для пользователя
        context['total_pending'] = SignatureService.get_pending_signatures_for_user(self.request.user).count()
        context['total_signed'] = DocumentSignature.objects.filter(
            actual_signer=self.request.user,
            status='signed'
        ).count()
        
        # Недавно подписанные
        context['recent_signatures'] = DocumentSignature.objects.filter(
            actual_signer=self.request.user,
            status='signed'
        ).order_by('-signed_at')[:5]
        
        # Истекшие подписи
        context['expired_signatures'] = DocumentSignature.objects.filter(
            required_signer=self.request.user,
            status='expired'
        ).order_by('-created_at')[:5]
        
        return context


class SignatureDetailView(LoginRequiredMixin, DetailView):
    """
    Детали подписи
    """
    model = DocumentSignature
    template_name = 'document_signatures/signature_detail.html'
    context_object_name = 'signature'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['document'] = self.object.content_object
            context['all_signatures'] = SignatureService.get_signatures_for_document(
                self.object.content_object
            )
            context['signature_status'] = SignatureService.get_document_signature_status(
                self.object.content_object
            )
        except Exception as e:
            context['document'] = None
            context['error'] = str(e)
        
        return context


class SignatureSignView(LoginRequiredMixin, View):
    """
    Представление для подписания документа
    """
    def post(self, request, pk):
        signature = get_object_or_404(DocumentSignature, pk=pk)
        notes = request.POST.get('notes', '')
        
        try:
            SignatureService.sign_document(signature.pk, request.user, notes)
            messages.success(request, 'Документ успешно подписан')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Документ успешно подписан',
                    'redirect_url': reverse_lazy('document_signatures:signature_list')
                })
            
            return redirect('document_signatures:signature_list')
            
        except PermissionError:
            error_msg = 'У вас нет прав для подписания этого документа'
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f'Ошибка при подписании: {e}'
            messages.error(request, error_msg)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            })
        
        return redirect('document_signatures:signature_detail', pk=pk)


class SignatureRejectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Представление для отклонения подписи
    """
    permission_required = 'document_signatures.can_reject_signature'
    
    def post(self, request, pk):
        signature = get_object_or_404(DocumentSignature, pk=pk)
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'Необходимо указать причину отклонения')
            return redirect('document_signatures:signature_detail', pk=pk)
        
        try:
            SignatureService.reject_document(signature.pk, request.user, reason)
            messages.success(request, 'Подпись отклонена')
            return redirect('document_signatures:signature_list')
            
        except Exception as e:
            messages.error(request, f'Ошибка при отклонении: {e}')
            return redirect('document_signatures:signature_detail', pk=pk)


class SignatureCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Представление для отмены подписи
    """
    permission_required = 'document_signatures.can_cancel_signature'
    
    def post(self, request, pk):
        signature = get_object_or_404(DocumentSignature, pk=pk)
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'Необходимо указать причину отмены')
            return redirect('document_signatures:signature_detail', pk=pk)
        
        try:
            SignatureService.cancel_document(signature.pk, request.user, reason)
            messages.success(request, 'Подпись отменена')
            return redirect('document_signatures:signature_list')
            
        except Exception as e:
            messages.error(request, f'Ошибка при отмене: {e}')
            return redirect('document_signatures:signature_detail', pk=pk)


class DocumentSignaturesView(LoginRequiredMixin, DetailView):
    """
    Просмотр всех подписей для документа
    """
    template_name = 'document_signatures/document_signatures.html'
    
    def get_object(self):
        """Получаем документ по content_type и object_id"""
        content_type_id = self.kwargs.get('content_type_id')
        object_id = self.kwargs.get('object_id')
        
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        return content_type.model_class().objects.get(pk=object_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['signatures'] = SignatureService.get_signatures_for_document(self.object)
        context['signature_status'] = SignatureService.get_document_signature_status(self.object)
        context['can_sign'] = self._can_user_sign_document(self.object)
        return context
    
    def _can_user_sign_document(self, document):
        """Проверяет, может ли текущий пользователь подписать документ"""
        signatures = SignatureService.get_signatures_for_document(document)
        pending_signatures = signatures.filter(status='pending')
        
        for signature in pending_signatures:
            if signature.can_sign(self.request.user):
                return True
        
        return False


class SignatureWorkflowListView(LoginRequiredMixin, ListView):
    """
    Список рабочих процессов подписей
    """
    model = SignatureWorkflow
    template_name = 'document_signatures/workflow_list.html'
    context_object_name = 'workflows'
    paginate_by = 20
    
    def get_queryset(self):
        return SignatureWorkflow.objects.filter(is_active=True).order_by('name')


class SignatureWorkflowDetailView(LoginRequiredMixin, DetailView):
    """
    Детали рабочего процесса
    """
    model = SignatureWorkflow
    template_name = 'document_signatures/workflow_detail.html'
    context_object_name = 'workflow'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_signatures'] = DocumentSignature.objects.filter(
            workflow=self.object,
            status='pending'
        ).count()
        context['completed_signatures'] = DocumentSignature.objects.filter(
            workflow=self.object,
            status='signed'
        ).count()
        return context


class SignatureWorkflowCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Создание нового рабочего процесса
    """
    model = SignatureWorkflow
    form_class = SignatureWorkflowForm
    template_name = 'document_signatures/workflow_form.html'
    permission_required = 'document_signatures.add_signatureworkflow'
    success_url = reverse_lazy('document_signatures:workflow_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Рабочий процесс успешно создан')
        return super().form_valid(form)


class SignatureWorkflowUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Редактирование рабочего процесса
    """
    model = SignatureWorkflow
    form_class = SignatureWorkflowForm
    template_name = 'document_signatures/workflow_form.html'
    permission_required = 'document_signatures.change_signatureworkflow'
    success_url = reverse_lazy('document_signatures:workflow_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Рабочий процесс успешно обновлен')
        return super().form_valid(form)


class SignatureTemplateListView(LoginRequiredMixin, ListView):
    """
    Список шаблонов подписей
    """
    model = SignatureTemplate
    template_name = 'document_signatures/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        return SignatureTemplate.objects.filter(is_active=True).order_by('name')


class SignatureTemplateCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Создание нового шаблона подписи
    """
    model = SignatureTemplate
    form_class = SignatureTemplateForm
    template_name = 'document_signatures/template_form.html'
    permission_required = 'document_signatures.add_signaturetemplate'
    success_url = reverse_lazy('document_signatures:template_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Шаблон подписи успешно создан')
        return super().form_valid(form)


class SignatureTemplateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Редактирование шаблона подписи
    """
    model = SignatureTemplate
    form_class = SignatureTemplateForm
    template_name = 'document_signatures/template_form.html'
    permission_required = 'document_signatures.change_signaturetemplate'
    success_url = reverse_lazy('document_signatures:template_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Шаблон подписи успешно обновлен')
        return super().form_valid(form)


class SignatureDashboardView(LoginRequiredMixin, View):
    """
    Дашборд с общей статистикой по подписям
    """
    template_name = 'document_signatures/dashboard.html'
    
    def get(self, request):
        from django.shortcuts import render
        
        # Статистика для текущего пользователя
        user_pending = SignatureService.get_pending_signatures_for_user(request.user).count()
        user_signed = DocumentSignature.objects.filter(
            actual_signer=request.user,
            status='signed'
        ).count()
        
        # Общая статистика (если есть права)
        if request.user.has_perm('document_signatures.view_all_signatures'):
            total_pending = DocumentSignature.objects.filter(status='pending').count()
            total_signed = DocumentSignature.objects.filter(status='signed').count()
            total_expired = DocumentSignature.objects.filter(status='expired').count()
            
            # Подписи по типам
            signatures_by_type = DocumentSignature.objects.values('signature_type').annotate(
                count=Count('id')
            ).order_by('signature_type')
            
            # Подписи по статусам
            signatures_by_status = DocumentSignature.objects.values('status').annotate(
                count=Count('id')
            ).order_by('status')
        else:
            total_pending = total_signed = total_expired = 0
            signatures_by_type = signatures_by_status = []
        
        context = {
            'user_pending': user_pending,
            'user_signed': user_signed,
            'total_pending': total_pending,
            'total_signed': total_signed,
            'total_expired': total_expired,
            'signatures_by_type': signatures_by_type,
            'signatures_by_status': signatures_by_status,
        }
        
        return render(request, self.template_name, context)


class SignatureAPIView(LoginRequiredMixin, View):
    """
    API для получения информации о подписях (для AJAX запросов)
    """
    def get(self, request, content_type_id, object_id):
        """Получает статус подписей для документа"""
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            document = content_type.model_class().objects.get(pk=object_id)
            
            signature_status = SignatureService.get_document_signature_status(document)
            signatures = SignatureService.get_signatures_for_document(document)
            
            data = {
                'status': signature_status,
                'signatures': [
                    {
                        'id': sig.pk,
                        'type': sig.get_signature_type_display(),
                        'status': sig.status,
                        'required_signer': sig.required_signer.get_full_name() or sig.required_signer.username,
                        'actual_signer': sig.actual_signer.get_full_name() or sig.actual_signer.username if sig.actual_signer else None,
                        'created_at': sig.created_at.isoformat() if sig.created_at else None,
                        'signed_at': sig.signed_at.isoformat() if sig.signed_at else None,
                        'can_sign': sig.can_sign(request.user) if sig.status == 'pending' else False,
                    }
                    for sig in signatures
                ]
            }
            
            return JsonResponse(data)
            
        except (ContentType.DoesNotExist, Exception) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def post(self, request, content_type_id, object_id):
        """Создает подписи для документа"""
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            document = content_type.model_class().objects.get(pk=object_id)
            
            workflow_type = request.POST.get('workflow_type', 'simple')
            signatures = SignatureService.create_signatures_for_document(document, workflow_type)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Создано {len(signatures)} подписей',
                'signatures_count': len(signatures)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
