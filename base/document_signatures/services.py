from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from .models import DocumentSignature, SignatureWorkflow, SignatureTemplate


class SignatureService:
    """
    Сервис для управления подписями документов
    """
    
    @staticmethod
    def create_signatures_for_document(document, workflow_type='simple', custom_workflow=None):
        """
        Создает необходимые подписи для документа
        
        Args:
            document: Экземпляр документа (LabTestResult, InstrumentalProcedureResult, etc.)
            workflow_type: Тип рабочего процесса ('simple', 'standard', 'complex', 'critical')
            custom_workflow: Пользовательский рабочий процесс (если указан)
        
        Returns:
            list: Список созданных подписей
        """
        # Получаем или создаем рабочий процесс
        if custom_workflow:
            workflow = custom_workflow
        else:
            try:
                # Сначала пытаемся найти существующий workflow
                workflow = SignatureWorkflow.objects.get(workflow_type=workflow_type)
            except SignatureWorkflow.DoesNotExist:
                # Если не найден, создаем новый
                workflow = SignatureWorkflow.objects.create(
                    workflow_type=workflow_type,
                    name=f'Рабочий процесс {workflow_type}',
                    require_doctor_signature=True,
                    require_head_signature=workflow_type in ['standard', 'complex', 'critical'],
                    require_chief_signature=workflow_type in ['complex', 'critical'],
                    require_patient_signature=workflow_type == 'critical',
                    auto_complete_on_doctor_signature=workflow_type == 'simple',
                    auto_complete_on_all_signatures=True,
                )
            except SignatureWorkflow.MultipleObjectsReturned:
                # Если найдено несколько, берем первый и логируем проблему
                workflow = SignatureWorkflow.objects.filter(workflow_type=workflow_type).first()
                print(f"Warning: Multiple SignatureWorkflow found for type '{workflow_type}'. Using first one.")
        
        # Определяем врача-исследователя
        doctor_user = getattr(document, 'author', None)
        if not doctor_user:
            # Пытаемся найти автора через другие поля
            doctor_user = getattr(document, 'created_by', None)
            if not doctor_user:
                raise ValueError("Не удалось определить автора документа")
        
        # Создаем подписи
        signatures = []
        
        if workflow.require_doctor_signature:
            timeout = None
            if workflow.doctor_signature_timeout_days:
                timeout = timezone.now() + timedelta(days=workflow.doctor_signature_timeout_days)
            
            signatures.append(DocumentSignature(
                content_type=ContentType.objects.get_for_model(document),
                object_id=document.pk,
                workflow=workflow,
                signature_type='doctor',
                required_signer=doctor_user,
                required_by=timeout
            ))
        
        if workflow.require_head_signature:
            # Находим заведующего отделением
            head_user = SignatureService._get_head_of_department(doctor_user)
            if head_user:
                timeout = None
                if workflow.head_signature_timeout_days:
                    timeout = timezone.now() + timedelta(days=workflow.head_signature_timeout_days)
                
                signatures.append(DocumentSignature(
                    content_type=ContentType.objects.get_for_model(document),
                    object_id=document.pk,
                    workflow=workflow,
                    signature_type='head_of_department',
                    required_signer=head_user,
                    required_by=timeout
                ))
        
        if workflow.require_chief_signature:
            # Находим главного врача
            chief_user = SignatureService._get_chief_physician()
            if chief_user:
                timeout = None
                if workflow.chief_signature_timeout_days:
                    timeout = timezone.now() + timedelta(days=workflow.chief_signature_timeout_days)
                
                signatures.append(DocumentSignature(
                    content_type=ContentType.objects.get_for_model(document),
                    object_id=document.pk,
                    workflow=workflow,
                    signature_type='chief_physician',
                    required_signer=chief_user,
                    required_by=timeout
                ))
        
        if workflow.require_patient_signature:
            # Пациент подписывает последним
            patient_user = SignatureService._get_patient_user(document)
            if patient_user:
                timeout = None
                if workflow.patient_signature_timeout_days:
                    timeout = timezone.now() + timedelta(days=workflow.patient_signature_timeout_days)
                
                signatures.append(DocumentSignature(
                    content_type=ContentType.objects.get_for_model(document),
                    object_id=document.pk,
                    workflow=workflow,
                    signature_type='patient',
                    required_signer=patient_user,
                    required_by=timeout
                ))
        
        # Сохраняем все подписи
        DocumentSignature.objects.bulk_create(signatures)
        return signatures
    
    @staticmethod
    def create_signatures_from_template(document, template_name):
        """
        Создает подписи на основе шаблона
        
        Args:
            document: Экземпляр документа
            template_name: Название шаблона
        
        Returns:
            list: Список созданных подписей
        """
        try:
            template = SignatureTemplate.objects.get(name=template_name, is_active=True)
            
            if not template.can_apply_to(document):
                raise ValueError(f"Шаблон '{template_name}' не может быть применен к данному типу документа")
            
            return SignatureService.create_signatures_for_document(
                document, 
                custom_workflow=template.workflow
            )
        except SignatureTemplate.DoesNotExist:
            raise ValueError(f"Шаблон '{template_name}' не найден")
    
    @staticmethod
    def sign_document(signature_id, user, notes=''):
        """
        Подписывает документ
        
        Args:
            signature_id: ID подписи
            user: Пользователь, который подписывает
            notes: Комментарии к подписи
        
        Returns:
            DocumentSignature: Обновленная подпись
        """
        try:
            signature = DocumentSignature.objects.get(pk=signature_id)
            signature.sign(user, notes)
            return signature
        except DocumentSignature.DoesNotExist:
            raise ValueError("Подпись не найдена")
        except PermissionError as e:
            raise e
    
    @staticmethod
    def reject_document(signature_id, user, reason):
        """
        Отклоняет документ
        
        Args:
            signature_id: ID подписи
            user: Пользователь, который отклоняет
            reason: Причина отклонения
        
        Returns:
            DocumentSignature: Обновленная подпись
        """
        try:
            signature = DocumentSignature.objects.get(pk=signature_id)
            signature.reject(user, reason)
            return signature
        except DocumentSignature.DoesNotExist:
            raise ValueError("Подпись не найдена")
        except PermissionError as e:
            raise e
    
    @staticmethod
    def cancel_document(signature_id, user, reason):
        """
        Отменяет подпись
        
        Args:
            signature_id: ID подписи
            user: Пользователь, который отменяет
            reason: Причина отмены
        
        Returns:
            DocumentSignature: Обновленная подпись
        """
        try:
            signature = DocumentSignature.objects.get(pk=signature_id)
            signature.cancel(user, reason)
            return signature
        except DocumentSignature.DoesNotExist:
            raise ValueError("Подпись не найдена")
        except PermissionError as e:
            raise e
    
    @staticmethod
    def get_pending_signatures_for_user(user):
        """
        Получает все ожидающие подписи для пользователя
        
        Args:
            user: Пользователь
        
        Returns:
            QuerySet: Подписи, ожидающие подписи пользователем
        """
        return DocumentSignature.objects.filter(
            required_signer=user,
            status='pending'
        ).select_related('content_type', 'workflow')
    
    @staticmethod
    def get_signatures_for_document(document):
        """
        Получает все подписи для документа
        
        Args:
            document: Экземпляр документа
        
        Returns:
            QuerySet: Все подписи для документа
        """
        content_type = ContentType.objects.get_for_model(document)
        return DocumentSignature.objects.filter(
            content_type=content_type,
            object_id=document.pk
        ).select_related('required_signer', 'actual_signer', 'workflow')
    
    @staticmethod
    def check_document_completion(document):
        """
        Проверяет, завершен ли документ (все подписи получены)
        
        Args:
            document: Экземпляр документа
        
        Returns:
            bool: True если документ завершен
        """
        signatures = SignatureService.get_signatures_for_document(document)
        if not signatures.exists():
            return False
        
        return all(signature.status == 'signed' for signature in signatures)
    
    @staticmethod
    def get_document_signature_status(document):
        """
        Получает статус подписей для документа
        
        Args:
            document: Экземпляр документа
        
        Returns:
            dict: Статус подписей
        """
        signatures = SignatureService.get_signatures_for_document(document)
        
        if not signatures.exists():
            return {
                'status': 'no_signatures',
                'text': 'Нет подписей',
                'color': 'secondary',
                'progress': 0,
                'total': 0,
                'signed': 0,
                'pending': 0
            }
        
        total = signatures.count()
        signed = signatures.filter(status='signed').count()
        pending = signatures.filter(status='pending').count()
        progress = int((signed / total) * 100) if total > 0 else 0
        
        if signed == total:
            status = 'all_signed'
            text = 'Все подписи получены'
            color = 'success'
        elif signed > 0:
            status = 'partially_signed'
            text = f'{signed} из {total} подписей'
            color = 'warning'
        else:
            status = 'no_signatures'
            text = f'Ожидает {total} подписей'
            color = 'info'
        
        return {
            'status': status,
            'text': text,
            'color': color,
            'progress': progress,
            'total': total,
            'signed': signed,
            'pending': pending
        }
    
    @staticmethod
    def get_expired_signatures():
        """
        Получает все истекшие подписи
        
        Returns:
            QuerySet: Истекшие подписи
        """
        return DocumentSignature.objects.filter(
            status='pending',
            required_by__lt=timezone.now()
        ).select_related('content_type', 'required_signer')
    
    @staticmethod
    def auto_expire_signatures():
        """
        Автоматически помечает истекшие подписи как истекшие
        
        Returns:
            int: Количество обновленных подписей
        """
        expired_signatures = SignatureService.get_expired_signatures()
        count = expired_signatures.update(status='expired')
        return count
    
    @staticmethod
    def _get_head_of_department(doctor_user):
        """
        Получает заведующего отделением для врача
        
        TODO: Реализовать логику получения заведующего отделением
        Пока возвращаем None - нужно будет реализовать
        """
        # Здесь должна быть логика получения заведующего отделением
        # Например, через профиль пользователя или роли
        return None
    
    @staticmethod
    def _get_chief_physician():
        """
        Получает главного врача
        
        TODO: Реализовать логику получения главного врача
        Пока возвращаем None - нужно будет реализовать
        """
        # Здесь должна быть логика получения главного врача
        # Например, через роли пользователей
        return None
    
    @staticmethod
    def _get_patient_user(document):
        """
        Получает пользователя-пациента для документа
        
        TODO: Реализовать логику получения пользователя-пациента
        Пока возвращаем None - нужно будет реализовать
        """
        # Здесь должна быть логика получения пользователя-пациента
        # Например, через связь с пациентом
        return None 