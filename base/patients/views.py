from django.shortcuts import render, get_object_or_404, redirect, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Patient
from .forms import PatientForm
from encounters.models import Encounter

def home(request):
    return render(request, 'patients/home.html')

def patient_list(request):
    query = request.GET.get('q')
    patients = Patient.objects.all()
    if query:
        words = [word.capitalize() for word in query.strip().split()]
        for word in words:
            patients = patients.filter(
                Q(family__icontains=word) |
                Q(given__icontains=word) |
                Q(middle__icontains=word)
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
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('patients:patient_list')
    else:
        form = PatientForm()
    return render(request, 'patients/form.html', {'form': form, 'title': 'Добавить пациента'})

def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/form.html', {'form': form, 'title': 'Редактировать пациента', 'patient': patient})

def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        patient.delete()
        return redirect('patients:patient_list')
    return render(request, 'patients/confirm_delete.html', {'patient': patient})