from django.db import models
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import Encounter
from .services.encounter_service import EncounterService
from patients.models import Patient
from .forms import EncounterForm, EncounterCloseForm, EncounterUpdateForm, EncounterReopenForm, EncounterUndoForm
from departments.models import Department, PatientDepartmentStatus

class EncounterDetailView(DetailView):
    model = Encounter
    template_name = 'encounters/detail.html'
    context_object_name = 'encounter'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        
        # Используем сервис для получения деталей
        service = EncounterService(encounter)
        details = service.get_encounter_details()
        
        context['documents'] = details['documents']
        context['encounter_number'] = details['encounter_number']
        context['is_active'] = details['is_active']
        context['has_documents'] = details['has_documents']
        
        # Добавляем информацию о командах
        context['command_history'] = service.get_command_history()
        context['last_command'] = service.get_last_command()
        
        return context

class EncounterCreateView(CreateView):
    model = Encounter
    form_class = EncounterForm
    template_name = 'encounters/form.html'

    def setup(self, request, *args, **kwargs):
        """Получаем пациента до основной логики."""
        super().setup(request, *args, **kwargs)
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])

    def form_valid(self, form):
        """Добавляем пациента и врача перед сохранением."""
        form.instance.patient = self.patient
        form.instance.doctor = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавляем в контекст пациента и заголовок."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['title'] = 'Новое обращение'
        return context
    
    def get_success_url(self):
        """Редирект после успешного создания."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterUpdateView(UpdateView):
    model = Encounter
    form_class = EncounterUpdateForm
    template_name = 'encounters/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['title'] = 'Редактировать обращение'
        return context

    def form_valid(self, form):
        old_outcome = self.get_object().outcome
        old_transfer_to_department = self.get_object().transfer_to_department

        # Если исход пустой, очищаем дату завершения
        if not form.cleaned_data.get('outcome'):
            form.instance.date_end = None
        # Если исход установлен, но дата завершения пуста, заполняем ее текущим временем
        elif form.cleaned_data.get('outcome') and not form.cleaned_data.get('date_end'):
            form.instance.date_end = timezone.now()

        # НОВАЯ ЛОГИКА: Проверка наличия документов перед сохранением, если случай закрывается
        # Случай считается закрытым, если outcome установлен и date_end установлен
        if form.cleaned_data.get('outcome') and form.instance.date_end:
            # Получаем актуальный объект Encounter, чтобы проверить его документы
            # (form.instance может еще не быть сохраненным в базе данных)
            current_encounter = self.get_object()
            if not current_encounter.documents.exists():
                messages.error(self.request, "Невозможно закрыть случай обращения: нет прикрепленных документов.")
                return self.form_invalid(form) # Возвращаем форму с ошибкой

        response = super().form_valid(form)

        new_outcome = self.object.outcome
        new_transfer_to_department = self.object.transfer_to_department

        # Логика для PatientDepartmentStatus при изменении перевода
        if old_outcome == 'transferred' and old_transfer_to_department:
            # Если раньше был перевод, и он изменился или отменился
            if new_outcome != 'transferred' or new_transfer_to_department != old_transfer_to_department:
                # Отменяем старую запись PatientDepartmentStatus
                patient_dept_status = PatientDepartmentStatus.objects.filter(
                    patient=self.object.patient,
                    department=old_transfer_to_department,
                    source_encounter=self.object
                ).order_by('-admission_date').first()
                if patient_dept_status:
                    if patient_dept_status.cancel_transfer():
                        messages.info(self.request, f"Предыдущий перевод в отделение «{old_transfer_to_department.name}» отменен.")
                    else:
                        messages.warning(self.request, f"Не удалось отменить предыдущий перевод в отделение «{old_transfer_to_department.name}».")

        if new_outcome == 'transferred' and new_transfer_to_department:
            # Если сейчас перевод, и он новый или изменился
            if old_outcome != 'transferred' or new_transfer_to_department != old_transfer_to_department:
                # Создаем новую запись PatientDepartmentStatus
                PatientDepartmentStatus.objects.create(
                    patient=self.object.patient,
                    department=new_transfer_to_department,
                    status='pending',
                    source_encounter=self.object
                )
                messages.success(self.request, f"Пациент переведен в отделение «{new_transfer_to_department.name}».")

        messages.success(self.request, "Обращение успешно обновлено.")
        return response

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})

class EncounterDeleteView(DeleteView):
    model = Encounter
    template_name = 'encounters/confirm_delete.html'

    def get_context_data(self, **kwargs):
        """Добавляем номер обращения для страницы подтверждения."""
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        context['encounter_number'] = Encounter.objects.filter(
            patient_id=encounter.patient_id,
            date_start__lt=encounter.date_start
        ).count() + 1
        return context
    
    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})
    
class EncounterCloseView(UpdateView):
    model = Encounter
    form_class = EncounterCloseForm
    template_name = 'encounters/close_form.html'

    def get_object(self, queryset=None):
        obj = get_object_or_404(Encounter, pk=self.kwargs['pk'], is_active=True)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Завершить обращение'
        context['encounter'] = self.get_object()
        context['encounter_number'] = Encounter.objects.filter(
            patient_id=self.get_object().patient_id,
            date_start__lt=self.get_object().date_start
        ).count() + 1
        return context

    def form_valid(self, form):
        encounter = self.get_object()
        
        try:
            # Используем новую форму с Command Pattern
            form.save(user=self.request.user)
            messages.success(self.request, "Случай обращения успешно закрыт.")
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f"Ошибка при закрытии: {e}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})
    
class EncounterReopenView(View):
    """
    Представление для возврата случая обращения в активное состояние.
    Обрабатывает POST-запрос для изменения состояния.
    """
    def post(self, request, pk, *args, **kwargs):
        encounter = get_object_or_404(Encounter, pk=pk)

        if encounter.is_active:
            messages.warning(request, "Случай обращения уже активен.")
            return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))

        # Здесь также можно добавить проверку прав доступа
        # if not request.user.has_perm('encounters.can_reopen_encounter'):
        #     messages.error(request, "У вас нет прав для активации случая обращения.")
        #     return HttpResponseForbidden()

        # Используем сервис с Command Pattern
        service = EncounterService(encounter)
        if service.reopen_encounter(user=request.user):
            messages.success(request, "Случай обращения успешно возвращен в активное состояние.")
        else:
            messages.error(request, "Не удалось вернуть случай обращения в активное состояние.")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))


class EncounterUndoView(View):
    """
    Представление для отмены последней операции.
    Обрабатывает POST-запрос для отмены операции.
    """
    def post(self, request, pk, *args, **kwargs):
        encounter = get_object_or_404(Encounter, pk=pk)

        # Используем сервис для отмены операции
        service = EncounterService(encounter)
        if service.undo_last_operation():
            messages.success(request, "Последняя операция успешно отменена.")
        else:
            messages.error(request, "Не удалось отменить последнюю операцию.")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))