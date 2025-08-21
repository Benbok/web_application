from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.urls import reverse


def get_content_type_id(model_class):
    """Получает ID типа контента для модели"""
    return ContentType.objects.get_for_model(model_class).id


def redirect_to_schedule_settings(assignment, assignment_type, request=None):
    """
    Перенаправляет на форму настройки расписания
    
    Args:
        assignment: объект назначения (TreatmentMedication, ExaminationLabTest, etc.)
        assignment_type: тип назначения (medication, lab_test, procedure)
        request: объект запроса для получения текущего URL (опционально)
    """
    content_type_id = get_content_type_id(assignment.__class__)
    
    url = reverse('clinical_scheduling:schedule_settings')
    params = {
        'assignment_type': assignment_type,
        'assignment_id': assignment.id,
        'content_type_id': content_type_id
    }
    
    # Добавляем текущий URL как параметр next, если request передан
    if request and hasattr(request, 'build_absolute_uri'):
        current_url = request.build_absolute_uri()
        params['next'] = current_url
    
    # Формируем URL с параметрами
    param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
    full_url = f"{url}?{param_string}"
    
    return redirect(full_url) 