from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.urls import reverse

from .models import Patient
from .forms import PatientForm
from newborns.forms import NewbornProfileForm
from encounters.models import Encounter

def home(request):
    latest_patients = Patient.objects.order_by('-created_at')[:5]
    total_patients = Patient.objects.count()
    return render(request, 'patients/home.html', {
        'latest_patients': latest_patients,
        'total_patients': total_patients,
    })

def patient_list(request):
    query = request.GET.get('q')
    patients = Patient.objects.all()
    if query:
        words = [word.capitalize() for word in query.strip().split()]
        for word in words:
            patients = patients.filter(
                Q(last_name__icontains=word) |
                Q(first_name__icontains=word) |
                Q(middle_name__icontains=word)
            )
    paginator = Paginator(patients, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, 'patients/list.html', {
        'patients': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
    })

def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    encounters = Encounter.objects.filter(patient=patient).order_by('-is_active', '-date_start')
    return render(request, 'patients/detail.html', {
        'patient': patient,
        'encounters': encounters,
    })

def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.patient_type = 'adult'  # фиксируем тип
            patient.save()
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, 'patients/form.html', {
        'form': form,
        'title': 'Добавить пациента',
        'is_newborn_creation_flow': False
    })

def newborn_create(request, parent_id):
    parent = get_object_or_404(Patient, pk=parent_id)
    if request.method == 'POST':
        form = PatientForm(request.POST)
        profile_form = NewbornProfileForm(request.POST)
        if form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                newborn = form.save(commit=False)
                newborn.patient_type = 'newborn'
                newborn.save()
                newborn.parents.add(parent)

                profile = profile_form.save(commit=False)
                profile.patient = newborn
                profile.save()

            return redirect('patients:patient_detail', pk=newborn.pk)
    else:
        form = PatientForm(initial={'patient_type': 'newborn'})
        profile_form = NewbornProfileForm()
    return render(request, 'patients/form.html', {
        'form': form,
        'newborn_form': profile_form,
        'title': f'Добавление новорожденного для {parent.full_name}',
        'is_newborn_creation_flow': True,
        'parent': parent
    })


def child_create(request, parent_id):
    """
    Создание пациента-ребенка, связанного с родителем.
    """
    parent = get_object_or_404(Patient, pk=parent_id)
    if request.method == 'POST':
        # Используем полную форму, так как у ребенка могут быть любые данные
        form = PatientForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.patient_type = 'child'  # Устанавливаем соответствующий тип
            child.save()
            child.parents.add(parent)  # Устанавливаем связь с родителем
            return redirect('patients:patient_detail', pk=child.pk)
    else:
        # В начальных данных передаем фамилию родителя и тип
        form = PatientForm(initial={'last_name': parent.last_name, 'patient_type': 'child'})

    return render(request, 'patients/form.html', {
        'form': form,
        'title': f'Добавление ребенка для {parent.full_name}',
        'parent': parent
    })


def teen_create(request, parent_id):
    """
    Создание пациента-подростка, связанного с родителем.
    Логика аналогична child_create.
    """
    parent = get_object_or_404(Patient, pk=parent_id)
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            teen = form.save(commit=False)
            teen.patient_type = 'teen'  # Устанавливаем тип "подросток"
            teen.save()
            teen.parents.add(parent)  # Устанавливаем связь
            return redirect('patients:patient_detail', pk=teen.pk)
    else:
        form = PatientForm(initial={'last_name': parent.last_name, 'patient_type': 'teen'})

    return render(request, 'patients/form.html', {
        'form': form,
        'title': f'Добавление подростка для {parent.full_name}',
        'parent': parent
    })

def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    newborn_profile = getattr(patient, '_newborn_profile', None)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        profile_form = NewbornProfileForm(request.POST, instance=newborn_profile) if newborn_profile else None
        if form.is_valid() and (not newborn_profile or profile_form.is_valid()):
            with transaction.atomic():
                form.save()
                if profile_form:
                    profile = profile_form.save(commit=False)
                    profile.patient = patient
                    profile.save()
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
        profile_form = NewbornProfileForm(instance=newborn_profile) if newborn_profile else None
    return render(request, 'patients/form.html', {
        'form': form,
        'newborn_form': profile_form,
        'title': 'Редактировать пациента',
        'is_newborn_creation_flow': patient.patient_type == 'newborn',
        'patient': patient
    })

def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        patient.delete()
        return redirect('patients:patient_list')
    return render(request, 'patients/confirm_delete.html', {'patient': patient})
