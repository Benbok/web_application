from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import Encounter
from patients.models import Patient
from .forms import EncounterForm, EncounterCloseForm, EncounterUpdateForm
from .services.encounter_service import EncounterService, EncounterValidationError
from .repositories.encounter_repository import EncounterRepository
from .factories.encounter_factory import EncounterFactory


class EncounterDetailView(DetailView):
    """Оптимизированное представление для детального просмотра случая обращения."""
    model = Encounter
    template_name = 'encounters/detail.html'
    context_object_name = 'encounter'

    def get_context_data(self, **kwargs):
        """Получение контекста с использованием сервиса."""
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        
        # Используем сервис для получения деталей
        service = EncounterService(encounter)
        encounter_details = service.get_encounter_details()
        
        context.update(encounter_details)
        return context


class EncounterCreateView(CreateView):
    """Оптимизированное представление для создания случая обращения."""
    model = Encounter
    form_class = EncounterForm
    template_name = 'encounters/form.html'

    def setup(self, request, *args, **kwargs):
        """Получение пациента до основной логики."""
        super().setup(request, *args, **kwargs)
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])

    def form_valid(self, form):
        """Создание случая обращения с использованием фабрики."""
        # Используем фабрику для создания
        encounter = EncounterFactory.create_encounter(
            patient=self.patient,
            doctor=self.request.user,
            date_start=form.cleaned_data['date_start']
        )
        
        self.object = encounter
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Добавление контекста для шаблона."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['title'] = 'Новое обращение'
        return context
    
    def get_success_url(self):
        """URL для перенаправления после создания."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterUpdateView(UpdateView):
    """Оптимизированное представление для обновления случая обращения."""
    model = Encounter
    form_class = EncounterUpdateForm
    template_name = 'encounters/form.html'

    def get_context_data(self, **kwargs):
        """Добавление контекста для шаблона."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['title'] = 'Редактировать обращение'
        return context

    def form_valid(self, form):
        """Обновление случая обращения с валидацией."""
        old_outcome = self.get_object().outcome
        old_transfer_to_department = self.get_object().transfer_to_department

        # Автоматическое управление датой завершения
        if not form.cleaned_data.get('outcome'):
            form.instance.date_end = None
        elif form.cleaned_data.get('outcome') and not form.cleaned_data.get('date_end'):
            form.instance.date_end = timezone.now()

        # Валидация наличия документов при закрытии
        if form.cleaned_data.get('outcome') and form.instance.date_end:
            service = EncounterService(self.get_object())
            if not service.validate_for_closing():
                messages.error(self.request, "Невозможно закрыть случай обращения: нет прикрепленных документов.")
                return self.form_invalid(form)

        response = super().form_valid(form)

        # Управление переводами в отделения
        self._handle_department_transfers(old_outcome, old_transfer_to_department)

        messages.success(self.request, "Обращение успешно обновлено.")
        return response

    def _handle_department_transfers(self, old_outcome, old_transfer_to_department):
        """Обработка переводов в отделения."""
        new_outcome = self.object.outcome
        new_transfer_to_department = self.object.transfer_to_department

        # Отмена старого перевода
        if old_outcome == 'transferred' and old_transfer_to_department:
            if new_outcome != 'transferred' or new_transfer_to_department != old_transfer_to_department:
                self._cancel_old_transfer(old_transfer_to_department)

        # Создание нового перевода
        if new_outcome == 'transferred' and new_transfer_to_department:
            if old_outcome != 'transferred' or new_transfer_to_department != old_transfer_to_department:
                self._create_new_transfer(new_transfer_to_department)

    def _cancel_old_transfer(self, old_department):
        """Отмена старого перевода."""
        from departments.models import PatientDepartmentStatus
        
        patient_dept_status = PatientDepartmentStatus.objects.filter(
            patient=self.object.patient,
            department=old_department,
            source_encounter=self.object
        ).order_by('-admission_date').first()
        
        if patient_dept_status and patient_dept_status.cancel_transfer():
            messages.info(self.request, f"Предыдущий перевод в отделение «{old_department.name}» отменен.")
        else:
            messages.warning(self.request, f"Не удалось отменить предыдущий перевод в отделение «{old_department.name}».")

    def _create_new_transfer(self, new_department):
        """Создание нового перевода."""
        from departments.models import PatientDepartmentStatus
        
        PatientDepartmentStatus.objects.create(
            patient=self.object.patient,
            department=new_department,
            status='pending',
            source_encounter=self.object
        )
        messages.success(self.request, f"Пациент переведен в отделение «{new_department.name}».")

    def get_success_url(self):
        """URL для перенаправления после обновления."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})


class EncounterDeleteView(DeleteView):
    """Оптимизированное представление для удаления случая обращения."""
    model = Encounter
    template_name = 'encounters/confirm_delete.html'

    def get_context_data(self, **kwargs):
        """Добавление номера обращения для страницы подтверждения."""
        context = super().get_context_data(**kwargs)
        encounter = self.get_object()
        
        # Используем репозиторий для вычисления номера
        repository = EncounterRepository()
        context['encounter_number'] = repository.get_encounter_number(encounter)
        
        return context
    
    def get_success_url(self):
        """URL для перенаправления после удаления."""
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})
    
    def delete(self, request, *args, **kwargs):
        """Удаление с использованием репозитория."""
        repository = EncounterRepository()
        encounter = self.get_object()
        repository.delete_encounter(encounter)
        
        messages.success(request, "Случай обращения успешно удален.")
        return redirect(self.get_success_url())


class EncounterCloseView(UpdateView):
    """Оптимизированное представление для закрытия случая обращения."""
    model = Encounter
    form_class = EncounterCloseForm
    template_name = 'encounters/close_form.html'

    def get_object(self, queryset=None):
        """Получение только активного случая обращения."""
        repository = EncounterRepository()
        obj = repository.get_active_by_id(self.kwargs['pk'])
        if not obj:
            raise Http404("Активный случай обращения не найден.")
        return obj

    def get_context_data(self, **kwargs):
        """Добавление контекста для формы закрытия."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Завершить обращение'
        context['encounter'] = self.get_object()
        
        # Используем репозиторий для вычисления номера
        repository = EncounterRepository()
        context['encounter_number'] = repository.get_encounter_number(self.get_object())
        
        return context

    def form_valid(self, form):
        """Закрытие случая обращения с использованием сервиса."""
        encounter = self.get_object()
        outcome = form.cleaned_data['outcome']
        transfer_department = form.cleaned_data.get('transfer_to_department')

        try:
            # Используем сервис для закрытия
            service = EncounterService(encounter)
            service.close_encounter(outcome, transfer_department)
            
            # Создание записи в отделении при переводе
            if outcome == 'transferred' and transfer_department:
                self._create_department_transfer(encounter, transfer_department)
                messages.success(self.request, f"Случай обращения успешно закрыт и пациент переведен в отделение «{transfer_department.name}».")
            else:
                messages.success(self.request, "Случай обращения успешно закрыт.")
            
            return redirect(self.get_success_url())
            
        except EncounterValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def _create_department_transfer(self, encounter, transfer_department):
        """Создание записи перевода в отделение."""
        from departments.models import PatientDepartmentStatus
        
        PatientDepartmentStatus.objects.create(
            patient=encounter.patient,
            department=transfer_department,
            status='pending',
            source_encounter=encounter
        )

    def get_success_url(self):
        """URL для перенаправления после закрытия."""
        return reverse('encounters:encounter_detail', kwargs={'pk': self.object.pk})
    
class EncounterReopenView(View):
    """Оптимизированное представление для возврата случая обращения в активное состояние."""
    
    def post(self, request, pk, *args, **kwargs):
        """Обработка POST-запроса для возврата случая."""
        repository = EncounterRepository()
        encounter = repository.get_by_id(pk)
        
        if not encounter:
            messages.error(request, "Случай обращения не найден.")
            return redirect('encounters:encounter_list')

        if encounter.is_active:
            messages.warning(request, "Случай обращения уже активен.")
            return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))

        try:
            # Используем сервис для возврата
            service = EncounterService(encounter)
            if service.reopen_encounter():
                messages.success(request, "Случай обращения успешно возвращен в активное состояние.")
            else:
                messages.error(request, "Не удалось вернуть случай обращения в активное состояние.")
                
        except Exception as e:
            messages.error(request, f"Ошибка при возврате случая: {str(e)}")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))


class EncounterArchiveView(View):
    """Оптимизированное представление для архивирования случая обращения."""
    
    def post(self, request, pk, *args, **kwargs):
        """Обработка POST-запроса для архивирования случая."""
        repository = EncounterRepository()
        encounter = repository.get_by_id(pk)
        
        if not encounter:
            messages.error(request, "Случай обращения не найден.")
            return redirect('encounters:encounter_list')

        try:
            # Используем сервис для архивирования
            service = EncounterService(encounter)
            service.archive_encounter()
            messages.success(request, "Случай обращения успешно архивирован.")
            
        except Exception as e:
            messages.error(request, f"Ошибка при архивировании: {str(e)}")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))


class EncounterUnarchiveView(View):
    """Оптимизированное представление для восстановления случая обращения из архива."""
    
    def post(self, request, pk, *args, **kwargs):
        """Обработка POST-запроса для восстановления случая."""
        repository = EncounterRepository()
        encounter = repository.get_by_id(pk)
        
        if not encounter:
            messages.error(request, "Случай обращения не найден.")
            return redirect('encounters:encounter_list')

        try:
            # Используем сервис для восстановления
            service = EncounterService(encounter)
            service.unarchive_encounter()
            messages.success(request, "Случай обращения успешно восстановлен из архива.")
            
        except Exception as e:
            messages.error(request, f"Ошибка при восстановлении: {str(e)}")

        return redirect(reverse('encounters:encounter_detail', kwargs={'pk': pk}))


class EncounterListView(DetailView):
    """Оптимизированное представление для списка случаев обращения пациента."""
    model = Patient
    template_name = 'encounters/patient_encounters.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        """Получение контекста со списком случаев обращения."""
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Используем репозиторий для получения данных
        repository = EncounterRepository()
        encounters = repository.get_by_patient(patient)
        
        context['encounters'] = encounters
        context['encounters_count'] = repository.get_patient_encounters_count(patient)
        context['active_encounters_count'] = encounters.filter(is_active=True).count()
        
        return context 