from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ValidationError
import json

from .models import ArchiveLog, ArchiveConfiguration
from .forms import ArchiveForm, RestoreForm, BulkArchiveForm, ArchiveFilterForm
from .services import ArchiveService


@login_required
def archive_record(request, app_label, model_name, pk):
    """
    Представление для архивирования записи
    """
    # Получаем модель и запись
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        model_class = content_type.model_class()
        instance = get_object_or_404(model_class, pk=pk)
    except (ContentType.DoesNotExist, AttributeError):
        raise Http404("Модель не найдена")
    
    # Проверяем поддержку архивирования
    if not hasattr(instance, 'is_archived'):
        messages.error(request, _("Данная модель не поддерживает архивирование"))
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Проверяем, что запись не уже архивирована
    if instance.is_archived:
        messages.warning(request, _("Запись уже архивирована"))
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    if request.method == 'POST':
        form = ArchiveForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            try:
                # Архивируем запись через универсальную систему
                from base.services import ArchiveService
                success = ArchiveService.archive_record(
                    instance=instance,
                    user=request.user,
                    reason=form.cleaned_data['reason'],
                    request=request,
                    cascade=form.cleaned_data.get('cascade', True)
                )
                
                messages.success(request, _("Запись успешно архивирована"))
                
                # Перенаправляем на страницу списка или детального просмотра
                if 'next' in request.GET:
                    return redirect(request.GET['next'])
                else:
                    return redirect(request.META.get('HTTP_REFERER', '/'))
                    
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
    else:
        form = ArchiveForm(instance=instance, user=request.user)
    
    context = {
        'form': form,
        'instance': instance,
        'model_name': model_name,
        'app_label': app_label,
    }
    
    return render(request, 'base/archive_form.html', context)


@login_required
def restore_record(request, app_label, model_name, pk):
    """
    Представление для восстановления записи из архива
    """
    # Получаем модель и запись
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        model_class = content_type.model_class()
        instance = get_object_or_404(model_class, pk=pk)
    except (ContentType.DoesNotExist, AttributeError):
        raise Http404("Модель не найдена")
    
    # Проверяем поддержку архивирования
    if not hasattr(instance, 'is_archived'):
        messages.error(request, _("Данная модель не поддерживает архивирование"))
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Проверяем, что запись архивирована
    if not instance.is_archived:
        messages.warning(request, _("Запись не архивирована"))
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    if request.method == 'POST':
        form = RestoreForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            try:
                # Восстанавливаем запись
                ArchiveService.restore_record(
                    instance=instance,
                    user=request.user,
                    request=request,
                    cascade=form.cleaned_data.get('cascade', True)
                )
                
                messages.success(request, _("Запись успешно восстановлена"))
                
                # Перенаправляем на страницу списка или детального просмотра
                if 'next' in request.GET:
                    return redirect(request.GET['next'])
                else:
                    return redirect(request.META.get('HTTP_REFERER', '/'))
                    
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
    else:
        form = RestoreForm(instance=instance, user=request.user)
    
    context = {
        'form': form,
        'instance': instance,
        'model_name': model_name,
        'app_label': app_label,
    }
    
    return render(request, 'base/restore_form.html', context)


@login_required
@require_POST
def bulk_archive(request, app_label, model_name):
    """
    Представление для массового архивирования записей
    """
    # Получаем модель
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        model_class = content_type.model_class()
    except (ContentType.DoesNotExist, AttributeError):
        raise Http404("Модель не найдена")
    
    # Получаем ID записей для архивирования
    record_ids = request.POST.getlist('record_ids')
    if not record_ids:
        messages.error(request, _("Не выбраны записи для архивирования"))
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Получаем QuerySet записей
    queryset = model_class.objects.filter(pk__in=record_ids)
    
    if request.method == 'POST':
        form = BulkArchiveForm(request.POST, queryset=queryset, user=request.user)
        if form.is_valid():
            try:
                # Архивируем записи
                archived_count = ArchiveService.bulk_archive(
                    queryset=queryset,
                    user=request.user,
                    reason=form.cleaned_data['reason'],
                    request=request
                )
                
                messages.success(
                    request, 
                    _("Успешно архивировано %(count)d записей") % {'count': archived_count}
                )
                
                # Перенаправляем на страницу списка
                if 'next' in request.GET:
                    return redirect(request.GET['next'])
                else:
                    return redirect(request.META.get('HTTP_REFERER', '/'))
                    
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
    else:
        form = BulkArchiveForm(queryset=queryset, user=request.user)
    
    context = {
        'form': form,
        'queryset': queryset,
        'model_name': model_name,
        'app_label': app_label,
    }
    
    return render(request, 'base/bulk_archive_form.html', context)


@login_required
def archive_list(request, app_label, model_name):
    """
    Представление для просмотра списка архивированных записей
    """
    # Получаем модель
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        model_class = content_type.model_class()
    except (ContentType.DoesNotExist, AttributeError):
        raise Http404("Модель не найдена")
    
    # Проверяем поддержку архивирования
    if not hasattr(model_class, 'is_archived'):
        messages.error(request, _("Данная модель не поддерживает архивирование"))
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Получаем конфигурацию архивирования
    config = ArchiveConfiguration.get_config(model_class)
    
    # Обрабатываем фильтры
    filter_form = ArchiveFilterForm(request.GET)
    queryset = model_class.objects.all()
    
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        archive_reason = filter_form.cleaned_data.get('archive_reason')
        archived_by = filter_form.cleaned_data.get('archived_by')
        archived_since = filter_form.cleaned_data.get('archived_since')
        archived_until = filter_form.cleaned_data.get('archived_until')
        
        # Применяем фильтры
        if status == 'active':
            queryset = queryset.filter(is_archived=False)
        elif status == 'archived':
            queryset = queryset.filter(is_archived=True)
        
        if archive_reason:
            queryset = queryset.filter(archive_reason__icontains=archive_reason)
        
        if archived_by:
            queryset = queryset.filter(archived_by=archived_by)
        
        if archived_since:
            queryset = queryset.filter(archived_at__gte=archived_since)
        
        if archived_until:
            queryset = queryset.filter(archived_at__lte=archived_until)
    
    # Пагинация
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'model_name': model_name,
        'app_label': app_label,
        'config': config,
    }
    
    return render(request, 'base/archive_list.html', context)


@login_required
def archive_logs(request):
    """
    Представление для просмотра логов архивирования
    """
    # Получаем логи архивирования
    logs = ArchiveLog.objects.all()
    
    # Фильтры
    action = request.GET.get('action')
    user_id = request.GET.get('user')
    model_name = request.GET.get('model')
    
    if action:
        logs = logs.filter(action=action)
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    if model_name:
        logs = logs.filter(content_type__model=model_name)
    
    # Пагинация
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'actions': ArchiveLog.ACTION_CHOICES,
        'models': ContentType.objects.filter(
            id__in=logs.values_list('content_type', flat=True).distinct()
        ),
    }
    
    return render(request, 'base/archive_logs.html', context)


@login_required
@csrf_exempt
def archive_ajax(request):
    """
    AJAX представление для архивирования/восстановления записей
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        app_label = data.get('app_label')
        model_name = data.get('model_name')
        pk = data.get('pk')
        reason = data.get('reason', '')
        
        if not all([action, app_label, model_name, pk]):
            return JsonResponse({'error': 'Не все параметры указаны'}, status=400)
        
        # Получаем модель и запись
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        model_class = content_type.model_class()
        instance = get_object_or_404(model_class, pk=pk)
        
        if action == 'archive':
            if instance.is_archived:
                return JsonResponse({'error': 'Запись уже архивирована'}, status=400)
            
            # Архивируем запись через универсальную систему
            from base.services import ArchiveService
            success = ArchiveService.archive_record(
                instance=instance,
                user=request.user,
                reason=reason,
                request=request,
                cascade=True
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Запись успешно архивирована',
                'is_archived': True
            })
            
        elif action == 'restore':
            if not instance.is_archived:
                return JsonResponse({'error': 'Запись не архивирована'}, status=400)
            
            ArchiveService.restore_record(
                instance=instance,
                user=request.user,
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Запись успешно восстановлена',
                'is_archived': False
            })
            
        else:
            return JsonResponse({'error': 'Неизвестное действие'}, status=400)
            
    except ContentType.DoesNotExist:
        return JsonResponse({'error': 'Модель не найдена'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except Exception as e:
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)


@login_required
def archive_configuration(request):
    """
    Представление для управления конфигурацией архивирования
    """
    if not request.user.is_staff:
        raise PermissionDenied("Доступ запрещен")
    
    configurations = ArchiveConfiguration.objects.all().order_by('content_type__app_label', 'content_type__model')
    
    if request.method == 'POST':
        # Обработка изменений конфигурации
        for config in configurations:
            config_id = f"config_{config.id}"
            if config_id in request.POST:
                config.is_archivable = f"{config_id}_archivable" in request.POST
                config.cascade_archive = f"{config_id}_cascade_archive" in request.POST
                config.cascade_restore = f"{config_id}_cascade_restore" in request.POST
                config.allow_restore = f"{config_id}_allow_restore" in request.POST
                config.require_reason = f"{config_id}_require_reason" in request.POST
                config.save()
        
        messages.success(request, _("Конфигурация архивирования обновлена"))
        return redirect('archive_configuration')
    
    context = {
        'configurations': configurations,
    }
    
    return render(request, 'base/archive_configuration.html', context)
