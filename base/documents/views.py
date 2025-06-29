from django.shortcuts import render, get_object_or_404, redirect
from .models import ClinicalDocument, DocumentTemplate
from .forms import ClinicalDocumentForm
from django.http import JsonResponse

def document_detail(request, pk):
    document = get_object_or_404(ClinicalDocument, pk=pk)
    return render(request, 'documents/detail.html', {'document': document})

def document_create(request, encounter_pk):
    from encounters.models import Encounter
    encounter = get_object_or_404(Encounter, pk=encounter_pk)
    if request.method == 'POST':
        form = ClinicalDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.encounter = encounter
            doc.author = request.user
            doc.save()
            return redirect('documents:document_detail', doc.pk)
    else:
        form = ClinicalDocumentForm()
    return render(request, 'documents/form.html', {'form': form, 'encounter': encounter, 'title': 'Новый документ'})

def document_update(request, pk):
    document = get_object_or_404(ClinicalDocument, pk=pk)
    encounter = document.encounter
    if request.method == 'POST':
        form = ClinicalDocumentForm(request.POST, request.FILES, instance=document, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('documents:document_detail', document.pk)
    else:
        form = ClinicalDocumentForm(instance=document, user=request.user)
    return render(request, 'documents/form.html', {
        'form': form, 
        'document': document, 
        'encounter': encounter,
        'title': 'Редактировать документ'})

def document_delete(request, pk):
    document = get_object_or_404(ClinicalDocument, pk=pk)
    encounter_pk = document.encounter.pk
    if request.method == 'POST':
        document.delete()
        return redirect('encounters:encounter_detail', encounter_pk)
    return render(request, 'documents/confirm_delete.html', {'document': document})

def template_data(request, pk):
    template = DocumentTemplate.objects.filter(pk=pk).first()
    if template:
        return JsonResponse({
            'title': template.name,
            'content': template.default_content,
        })
    return JsonResponse({}, status=404)