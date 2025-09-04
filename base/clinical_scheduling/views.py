from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import url_has_allowed_host_and_scheme

from .models import ScheduledAppointment
from .services import ClinicalSchedulingService
from .forms import ScheduleSettingsForm


def get_safe_return_url(request, default_url='clinical_scheduling:dashboard'):
    """Получить безопасный URL для возврата"""
    # Приоритет отдаем параметру next
    next_url = request.GET.get('next')
    
    if next_url:
        # Проверяем безопасность URL
        if url_has_allowed_host_and_scheme(
            next_url, 
            allowed_hosts={request.get_host()}, 
            require_https=request.is_secure()
        ):
            return next_url
    
    # Если нет параметра next, проверяем HTTP_REFERER
    referer = request.META.get('HTTP_REFERER')
    if referer:
        # Проверяем безопасность URL
        if url_has_allowed_host_and_scheme(
            referer, 
            allowed_hosts={request.get_host()}, 
            require_https=request.is_secure()
        ):
            # Не возвращаемся на ту же страницу
            if referer != request.build_absolute_uri():
                return referer
    
    return reverse_lazy(default_url)


def dashboard(request):
    """Главная страница планировщика"""
    # Получаем параметры фильтрации
    patient_id = request.GET.get('patient_id')
    department_id = request.GET.get('department_id')
    encounter_id = request.GET.get('encounter_id')
    show_all = request.GET.get('show_all') == 'true'
    
    # Базовый queryset
    queryset = ScheduledAppointment.objects.select_related(
        'patient', 'created_department', 'encounter', 'executed_by', 'rejected_by'
    ).exclude(
        execution_status='canceled'  # Исключаем отмененные назначения
    )
    
    # Проверяем, есть ли фильтр по дате
    date_filter = request.GET.get('date_filter')
    if date_filter == 'today':
        # Для фильтра "Сегодня" сортируем только по времени
        queryset = queryset.order_by('scheduled_time')
    else:
        # Для остальных случаев сортируем по дате и времени
        queryset = queryset.order_by('-scheduled_date', 'scheduled_time')
    
    # Применяем фильтры
    if patient_id:
        queryset = queryset.filter(patient_id=patient_id)
    
    if department_id:
        queryset = queryset.filter(created_department_id=department_id)
    
    if encounter_id:
        queryset = queryset.filter(encounter_id=encounter_id)
    
    # Получаем статистику
    total_appointments = queryset.count()
    completed_appointments = queryset.filter(execution_status='completed').count()
    pending_appointments = queryset.filter(execution_status='scheduled').count()
    overdue_appointments = queryset.filter(
        scheduled_date__lt=timezone.now().date(),
        execution_status__in=['scheduled', 'partial']
    ).count()
    
    # Определяем, сколько записей показывать
    if show_all:
        appointments = queryset
        show_all_param = 'true'
    else:
        appointments = queryset[:50]  # Ограничиваем для производительности
        show_all_param = 'false'
    
    context = {
        'appointments': appointments,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'overdue_appointments': overdue_appointments,
        'filters': {
            'patient_id': patient_id,
            'department_id': department_id,
            'encounter_id': encounter_id,
            'show_all': show_all_param,
        },
        'show_all': show_all,
        'return_url': get_safe_return_url(request),
    }
    
    return render(request, 'clinical_scheduling/dashboard.html', context)


@login_required
def schedule_settings(request):
    """Форма для настройки параметров расписания"""
    if request.method == 'POST':
        # Получаем параметры из POST
        assignment_type = request.POST.get('assignment_type')
        assignment_id = request.POST.get('assignment_id')
        content_type_id = request.POST.get('content_type_id')
        
        # Создаем форму с типом назначения
        form = ScheduleSettingsForm(request.POST, assignment_type=assignment_type)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Получаем объект назначения
                    content_type = ContentType.objects.get(id=content_type_id)
                    assignment = content_type.model_class().objects.get(id=assignment_id)
                    
                    # Создаем расписание с указанными параметрами
                    schedules = ClinicalSchedulingService.create_schedule_for_assignment(
                        assignment=assignment,
                        user=request.user,
                        start_date=form.cleaned_data['start_date'],
                        first_time=form.cleaned_data['first_time'],
                        times_per_day=form.cleaned_data['times_per_day'],
                        duration_days=form.cleaned_data['duration_days']
                    )
                    
                    if schedules:
                        messages.success(
                            request, 
                            f'Создано {len(schedules)} записей в расписании для назначения'
                        )
                        
                        # Перенаправляем на dashboard с фильтрами
                        if hasattr(assignment, 'treatment_plan') and assignment.treatment_plan.encounter:
                            encounter = assignment.treatment_plan.encounter
                            return redirect(f"{reverse_lazy('clinical_scheduling:dashboard')}?patient_id={encounter.patient.pk}&encounter_id={encounter.pk}")
                        elif hasattr(assignment, 'examination_plan') and assignment.examination_plan.encounter:
                            encounter = assignment.examination_plan.encounter
                            return redirect(f"{reverse_lazy('clinical_scheduling:dashboard')}?patient_id={encounter.patient.pk}&encounter_id={encounter.pk}")
                        else:
                            return redirect('clinical_scheduling:dashboard')
                    else:
                        messages.warning(request, 'Расписание не было создано')
                        
            except Exception as e:
                messages.error(request, f'Ошибка при создании расписания: {str(e)}')
                return redirect('clinical_scheduling:dashboard')
    else:
        # GET запрос - показываем форму
        assignment_type = request.GET.get('assignment_type')
        assignment_id = request.GET.get('assignment_id')
        content_type_id = request.GET.get('content_type_id')
        
        if not all([assignment_type, assignment_id, content_type_id]):
            messages.error(request, 'Недостаточно параметров для настройки расписания')
            return redirect('clinical_scheduling:dashboard')
        
        # Получаем объект назначения для отображения информации
        try:
            content_type = ContentType.objects.get(id=content_type_id)
            assignment = content_type.model_class().objects.get(id=assignment_id)
        except (ContentType.DoesNotExist, ObjectDoesNotExist):
            messages.error(request, 'Назначение не найдено')
            return redirect('clinical_scheduling:dashboard')
        
        form = ScheduleSettingsForm(assignment_type=assignment_type)
    
    # Получаем URL для возврата
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER')
    
    # Проверяем безопасность URL
    if next_url and not url_has_allowed_host_and_scheme(
        next_url, 
        allowed_hosts={request.get_host()}, 
        require_https=request.is_secure()
    ):
        next_url = None
    
    # Устанавливаем URL по умолчанию, если безопасный URL не найден
    if not next_url:
        next_url = reverse_lazy('clinical_scheduling:dashboard')
    
    context = {
        'form': form,
        'assignment_type': assignment_type,
        'assignment_id': assignment_id,
        'content_type_id': content_type_id,
        'assignment': assignment,  # Добавляем объект назначения в контекст
        'next_url': next_url,  # Добавляем URL для возврата
        'return_url': get_safe_return_url(request),
    }
    
    return render(request, 'clinical_scheduling/schedule_settings.html', context)


@login_required
def mark_as_completed(request, appointment_id):
    """Отметить назначение как выполненное"""
    appointment = get_object_or_404(ScheduledAppointment, id=appointment_id)
    
    if not appointment.can_be_edited_by_user(request.user):
        messages.error(request, 'У вас нет прав для редактирования этого назначения')
        return redirect('clinical_scheduling:dashboard')
    
    if request.method == 'POST':
        appointment.execution_status = 'completed'
        appointment.executed_by = request.user
        appointment.executed_at = timezone.now()
        appointment.save()
        
        messages.success(request, 'Назначение отмечено как выполненное')
        # Используем безопасный URL для возврата
        return_url = get_safe_return_url(request)
        return redirect(return_url)
    
    context = {
        'appointment': appointment,
        'return_url': get_safe_return_url(request),
    }
    return render(request, 'clinical_scheduling/mark_completed.html', context)


@login_required
def mark_as_rejected(request, appointment_id):
    """Отметить назначение как отклоненное"""
    appointment = get_object_or_404(ScheduledAppointment, id=appointment_id)
    
    if not appointment.can_be_edited_by_user(request.user):
        messages.error(request, 'У вас нет прав для редактирования этого назначения')
        return redirect('clinical_scheduling:dashboard')
    
    if request.method == 'POST':
        appointment.execution_status = 'rejected'
        appointment.rejected_by = request.user
        appointment.rejected_at = timezone.now()
        appointment.rejection_reason = request.POST.get('rejection_reason', '')
        appointment.save()
        
        messages.success(request, 'Назначение отмечено как отклоненное')
        # Используем безопасный URL для возврата
        return_url = get_safe_return_url(request)
        return redirect(return_url)
    
    context = {
        'appointment': appointment,
        'return_url': get_safe_return_url(request),
    }
    return render(request, 'clinical_scheduling/mark_rejected.html', context)


@login_required
def mark_as_skipped(request, appointment_id):
    """Отметить назначение как пропущенное"""
    appointment = get_object_or_404(ScheduledAppointment, id=appointment_id)
    
    if not appointment.can_be_edited_by_user(request.user):
        messages.error(request, 'У вас нет прав для редактирования этого назначения')
        return redirect('clinical_scheduling:dashboard')
    
    if request.method == 'POST':
        appointment.execution_status = 'skipped'
        appointment.executed_by = request.user
        appointment.executed_at = timezone.now()
        appointment.save()
        
        messages.success(request, 'Назначение отмечено как пропущенное')
        # Используем безопасный URL для возврата
        return_url = get_safe_return_url(request)
        return redirect(return_url)
    
    context = {
        'appointment': appointment,
        'return_url': get_safe_return_url(request),
    }
    return render(request, 'clinical_scheduling/mark_skipped.html', context)


@login_required
def mark_as_partial(request, appointment_id):
    """Отметить назначение как частично выполненное"""
    appointment = get_object_or_404(ScheduledAppointment, id=appointment_id)
    
    if not appointment.can_be_edited_by_user(request.user):
        messages.error(request, 'У вас нет прав для редактирования этого назначения')
        return redirect('clinical_scheduling:dashboard')
    
    # Используем безопасный URL для возврата
    return_url = get_safe_return_url(request)
    
    if request.method == 'POST':
        appointment.execution_status = 'partial'
        appointment.executed_by = request.user
        appointment.executed_at = timezone.now()
        appointment.notes = request.POST.get('notes', '')
        appointment.save()
        
        messages.success(request, 'Назначение отмечено как частично выполненное')
        return redirect(return_url)
    
    context = {
        'appointment': appointment,
        'return_url': return_url,
    }
    return render(request, 'clinical_scheduling/mark_partial.html', context)


def appointment_detail(request, appointment_id):
    """Детальная информация о назначении"""
    appointment = get_object_or_404(ScheduledAppointment, id=appointment_id)
    
    context = {
        'appointment': appointment,
        'can_edit': appointment.can_be_edited_by_user(request.user) if request.user.is_authenticated else False,
        'return_url': get_safe_return_url(request),
    }
    
    return render(request, 'clinical_scheduling/appointment_detail.html', context)





def patient_schedule(request, patient_id):
    """Расписание конкретного пациента"""
    from patients.models import Patient
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Проверяем права доступа
    if request.user.is_authenticated and not request.user.is_superuser:
        try:
            user_department = request.user.department
            # Здесь можно добавить дополнительную логику проверки прав
        except:
            messages.error(request, 'У вас нет прав для просмотра расписания этого пациента')
            return redirect('clinical_scheduling:dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    schedules = ClinicalSchedulingService.get_patient_schedule(
        patient=patient,
        start_date=start_date,
        end_date=end_date
    )
    
    context = {
        'patient': patient,
        'schedules': schedules,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
        },
        'return_url': get_safe_return_url(request),
    }
    
    return render(request, 'clinical_scheduling/patient_schedule.html', context)
