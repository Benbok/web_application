from django.shortcuts import render, get_object_or_404, redirect
from .models import Encounter
from patients.models import Patient
from .forms import EncounterForm
from documents.models import ClinicalDocument
from documents.forms import ClinicalDocumentForm


def encounter_detail(request, pk):
    encounter = get_object_or_404(Encounter, pk=pk)
    documents = ClinicalDocument.objects.filter(encounter=encounter)
    if request.method == 'POST':
        document_form = ClinicalDocumentForm(request.POST, request.FILES, user=request.user)
        if document_form.is_valid():
            doc = document_form.save(commit=False)
            doc.encounter = encounter
            doc.author = request.user
            doc.save()
            return redirect('encounters:encounter_detail', pk=encounter.pk)
    else:
        document_form = ClinicalDocumentForm(user=request.user)
    # Порядковый номер обращения
    encounters = encounter.patient.encounters.order_by('date_start', 'pk')
    encounter_number = list(encounters).index(encounter) + 1
    return render(request, 'encounters/detail.html', {
        'encounter': encounter,
        'encounter_number': encounter_number,
        'documents': documents,
        'document_form': document_form,
    })

def encounter_create(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = EncounterForm(request.POST)
        if form.is_valid():
            encounter = form.save(commit=False)
            encounter.patient = patient
            encounter.doctor = request.user
            encounter.save()
            return redirect('encounters:encounter_detail', pk=encounter.pk)
    else:
        form = EncounterForm()
    return render(request, 'encounters/form.html', {
        'form': form,
        'title': 'Новое обращение',
        'patient': patient,
    })

def encounter_update(request, pk):
    encounter = get_object_or_404(Encounter, pk=pk)
    patient = encounter.patient
    if request.method == 'POST':
        form = EncounterForm(request.POST, instance=encounter)
        if form.is_valid():
            form.save()
            return redirect('encounters:encounter_detail', pk=encounter.pk)
    else:
        form = EncounterForm(instance=encounter)
    return render(request, 'encounters/form.html', {
        'form': form,
        'title': 'Редактировать обращение',
        'patient': patient,
    })

def encounter_delete(request, pk):
    encounter = get_object_or_404(Encounter, pk=pk)
    encounters = encounter.patient.encounters.order_by('date_start', 'pk')
    encounter_number = list(encounters).index(encounter) + 1
    patient_pk = encounter.patient.pk 
    if request.method == 'POST':
        encounter.delete()
        return redirect('patient_detail', patient_pk)
    return render(request, 'encounters/confirm_delete.html', {
        'encounter': encounter,
        'encounter_number': encounter_number,
    })