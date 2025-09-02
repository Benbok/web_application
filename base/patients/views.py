from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from urllib.parse import urlencode
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Patient, PatientContact, PatientAddress, PatientDocument
from .forms import PatientForm, PatientContactForm, PatientAddressForm, PatientDocumentForm
from newborns.forms import NewbornProfileForm
from encounters.models import Encounter
from appointments.models import AppointmentEvent


def save_patient_with_related(patient_form, contact_form, address_form, document_form,
                              newborn_form=None, patient_type=None, parent=None):
    """Сохраняет пациента и все связанные модели в одной транзакции."""
    with transaction.atomic():
        patient = patient_form.save(commit=False)
        if patient_type:
            patient.patient_type = patient_type  # Автоматически задаём тип пациента (при создании)
        patient.save()

        contact = contact_form.save(commit=False)
        contact.patient = patient
        contact.save()

        address = address_form.save(commit=False)
        address.patient = patient
        address.save()

        document = document_form.save(commit=False)
        document.patient = patient
        document.save()

        if newborn_form:
            profile = newborn_form.save(commit=False)
            profile.patient = patient
            profile.save()

        if parent:
            patient.parents.add(parent)

        return patient

@login_required
def home(request):
    latest_patients = Patient.objects.order_by('-created_at')[:5]
    total_patients = Patient.objects.count()
    # Подсчёт приёмов на сегодня для текущего врача
    today = timezone.localdate()
    user = request.user
    todays_appointments = 0
    if user.is_authenticated and hasattr(user, 'doctor_profile'):
        todays_appointments = AppointmentEvent.objects.filter(
            schedule__doctor=user,
            start__date=today,
            status='scheduled'
        ).count()
    return render(request, 'patients/home.html', {
        'latest_patients': latest_patients,
        'total_patients': total_patients,
        'todays_appointments': todays_appointments,
    })


@login_required
def patient_list(request):
    query = request.GET.get('q')
    patients = Patient.objects.all()
    
    if query:
        # Нормализуем поисковый запрос - приводим к нижнему регистру
        query = query.strip().lower()
        words = [word.strip() for word in query.split()]
        
        # Создаем Q-объект для поиска по любому из слов
        q_objects = Q()
        for word in words:
            if word:  # Проверяем, что слово не пустое
                q_objects |= (
                    Q(last_name__icontains=word) |
                    Q(first_name__icontains=word) |
                    Q(middle_name__icontains=word) |
                    # Дополнительный поиск в верхнем регистре
                    Q(last_name__icontains=word.capitalize()) |
                    Q(first_name__icontains=word.capitalize()) |
                    Q(middle_name__icontains=word.capitalize())
                )
        patients = patients.filter(q_objects)
    
    paginator = Paginator(patients, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, 'patients/list.html', {
        'patients': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
    })


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    encounters = patient.encounters.all().order_by('-is_active', '-date_start')

    # Добавляем связанные данные:
    contact = getattr(patient, 'contact', None)
    address = getattr(patient, 'address', None)
    document = getattr(patient, 'document', None)

    return render(request, 'patients/detail.html', {
        'patient': patient,
        'encounters': encounters,
        'contact': contact,
        'address': address,
        'document': document,
    })


@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        contact_form = PatientContactForm(request.POST)
        address_form = PatientAddressForm(request.POST)
        document_form = PatientDocumentForm(request.POST)
        if all([form.is_valid(), contact_form.is_valid(), address_form.is_valid(), document_form.is_valid()]):
            patient = save_patient_with_related(
                form, contact_form, address_form, document_form,
                patient_type=Patient.PatientType.ADULT
            )
            action = request.POST.get('action')
            if action == 'save_and_appointment':
                redirect_url = f"{reverse('appointments:create')}?{urlencode({'patient_id': patient.pk})}"
                return redirect(redirect_url)
            else:
                return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm()
        contact_form = PatientContactForm()
        address_form = PatientAddressForm()
        document_form = PatientDocumentForm()

    return render(request, 'patients/form.html', {
        'form': form,
        'contact_form': contact_form,
        'address_form': address_form,
        'document_form': document_form,
        'title': 'Добавить пациента',
    })


@login_required
def newborn_create(request, parent_id):
    parent = get_object_or_404(Patient, pk=parent_id)
    if request.method == 'POST':
        form = PatientForm(request.POST)
        profile_form = NewbornProfileForm(request.POST)
        contact_form = PatientContactForm(request.POST)
        address_form = PatientAddressForm(request.POST)
        document_form = PatientDocumentForm(request.POST)
        if all([form.is_valid(), profile_form.is_valid(), contact_form.is_valid(), address_form.is_valid(),
                document_form.is_valid()]):
            patient = save_patient_with_related(
                form, contact_form, address_form, document_form,
                newborn_form=profile_form,
                patient_type=Patient.PatientType.NEWBORN,
                parent=parent
            )
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm(initial={'patient_type': 'newborn'})
        profile_form = NewbornProfileForm()
    return render(request, 'patients/form.html', {
        'form': form,
        'newborn_form': profile_form,
        'title': f'Добавление новорождённого для {parent.full_name}',
        'is_newborn_creation_flow': True,
        'parent': parent,
    })


@login_required
def child_create(request, parent_id):
    parent = get_object_or_404(Patient, pk=parent_id)
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                child = form.save(commit=False)
                child.patient_type = 'child'
                child.save()
                child.parents.add(parent)
                PatientContact.objects.create(patient=child)
                PatientAddress.objects.create(patient=child)
                PatientDocument.objects.create(patient=child)
            return redirect('patients:patient_detail', pk=child.pk)
    else:
        form = PatientForm(initial={'last_name': parent.last_name, 'patient_type': 'child'})
    return render(request, 'patients/form.html', {
        'form': form,
        'title': f'Добавление ребёнка для {parent.full_name}',
        'parent': parent,
    })


@login_required
def teen_create(request, parent_id):
    parent = get_object_or_404(Patient, pk=parent_id)
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                teen = form.save(commit=False)
                teen.patient_type = 'teen'
                teen.save()
                teen.parents.add(parent)
                PatientContact.objects.create(patient=teen)
                PatientAddress.objects.create(patient=teen)
                PatientDocument.objects.create(patient=teen)
            return redirect('patients:patient_detail', pk=teen.pk)
    else:
        form = PatientForm(initial={'last_name': parent.last_name, 'patient_type': 'teen'})
    return render(request, 'patients/form.html', {
        'form': form,
        'title': f'Добавление подростка для {parent.full_name}',
        'parent': parent,
    })


@login_required
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    newborn_profile = getattr(patient, '_newborn_profile', None)
    encounter_pk = request.GET.get('encounter_pk')

    # Загружаем связанные данные (контакты, адреса, документы)
    contact = getattr(patient, 'contact', None)
    address = getattr(patient, 'address', None)
    document = getattr(patient, 'document', None)

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        contact_form = PatientContactForm(request.POST, instance=contact)
        address_form = PatientAddressForm(request.POST, instance=address)
        document_form = PatientDocumentForm(request.POST, instance=document)
        profile_form = NewbornProfileForm(request.POST, instance=newborn_profile) if newborn_profile else None

        forms = [form, contact_form, address_form, document_form]
        if profile_form:
            forms.append(profile_form)

        if all(f.is_valid() for f in forms):
            patient = save_patient_with_related(
                form, contact_form, address_form, document_form,
                newborn_form=profile_form
            )

            if encounter_pk:
                return redirect('encounters:encounter_detail', pk=encounter_pk)
            else:
                return redirect('patients:patient_detail', pk=patient.pk)

    else:
        form = PatientForm(instance=patient)
        contact_form = PatientContactForm(instance=contact)
        address_form = PatientAddressForm(instance=address)
        document_form = PatientDocumentForm(instance=document)
        profile_form = NewbornProfileForm(instance=newborn_profile) if newborn_profile else None

    context = {
        'form': form,
        'contact_form': contact_form,
        'address_form': address_form,
        'document_form': document_form,
        'newborn_form': profile_form,
        'title': 'Редактировать пациента',
        'patient': patient,
    }

    if encounter_pk:
        context['encounter_pk'] = encounter_pk

    return render(request, 'patients/form.html', context)


@login_required
def patient_archive(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if patient.is_archived:
        from django.contrib import messages
        messages.warning(request, 'Этот пациент уже архивирован')
        return redirect('patients:patient_detail', pk=pk)
    
    if request.method == "POST":
        reason = request.POST.get('reason', '')
        
        try:
            # Используем универсальную систему архивирования
            from base.services import ArchiveService
            success = ArchiveService.archive_record(
                instance=patient,
                user=request.user,
                reason=reason,
                request=request,
                cascade=True
            )
            
            if success:
                from django.contrib import messages
                messages.success(request, f"Пациент {patient.get_full_name_with_age()} успешно архивирован.")
            else:
                from django.contrib import messages
                messages.error(request, f"Не удалось архивировать пациента {patient.get_full_name_with_age()}.")
                
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Ошибка при архивировании пациента: {str(e)}")
        
        return redirect('patients:patient_list')
    
    return render(request, 'patients/confirm_archive.html', {'patient': patient})


@login_required
def patient_restore(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if not patient.is_archived:
        from django.contrib import messages
        messages.warning(request, 'Этот пациент не архивирован')
        return redirect('patients:patient_detail', pk=pk)
    
    try:
        # Используем универсальную систему восстановления
        from base.services import ArchiveService
        success = ArchiveService.restore_record(
            instance=patient,
            user=request.user,
            request=request,
            cascade=True
        )
        
        if success:
            from django.contrib import messages
            messages.success(request, f"Пациент {patient.get_full_name_with_age()} успешно восстановлен.")
        else:
            from django.contrib import messages
            messages.error(request, f"Не удалось восстановить пациента {patient.get_full_name_with_age()}.")
            
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f"Ошибка при восстановлении пациента: {str(e)}")
    
    return redirect('patients:patient_detail', pk=pk)