from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import DocumentSignature
from .services import SignatureService


# Сигнал о подписании документа
document_signed = Signal()

# Сигнал о завершении всех подписей документа
document_fully_signed = Signal()

# Сигнал об отклонении подписи
signature_rejected = Signal()

# Сигнал об отмене подписи
signature_cancelled = Signal()

# Сигнал об истечении срока подписи
signature_expired = Signal()


@receiver(post_save, sender=DocumentSignature)
def handle_document_signature_change(sender, instance, created, **kwargs):
    """
    Обрабатывает изменения в подписях документов
    """
    if created:
        # Новая подпись создана - ничего не делаем
        return
    
    if instance.status == 'signed':
        # Подпись получена - проверяем завершение документа
        document = instance.content_object
        
        if SignatureService.check_document_completion(document):
            # Документ полностью подписан - отправляем сигнал
            document_fully_signed.send(
                sender=sender, 
                document=document, 
                signatures=SignatureService.get_signatures_for_document(document)
            )
            
            # Обновляем статус в examination_management если это результат исследования
            _update_examination_status(document, instance.actual_signer)
    
    elif instance.status == 'rejected':
        # Подпись отклонена - отправляем сигнал
        signature_rejected.send(sender=sender, instance=instance)
    
    elif instance.status == 'cancelled':
        # Подпись отменена - отправляем сигнал
        signature_cancelled.send(sender=sender, instance=instance)
    
    elif instance.status == 'expired':
        # Подпись истекла - отправляем сигнал
        signature_expired.send(sender=sender, instance=instance)


def _update_examination_status(document, signer):
    """
    Обновляет статус в examination_management после подписания
    
    Args:
        document: Подписанный документ
        signer: Пользователь, который подписал
    """
    try:
        # Проверяем, есть ли связь с examination_management
        if hasattr(document, 'examination_plan'):
            # Это результат исследования - обновляем статус
            examination_item = _find_examination_item(document)
            if examination_item:
                examination_item.status = 'completed'
                examination_item.completed_at = timezone.now()
                examination_item.completed_by = signer
                examination_item.save()
                
                # Синхронизируем с clinical_scheduling
                _sync_with_clinical_scheduling(examination_item, signer)
    
    except Exception as e:
        # Логируем ошибку, но не прерываем процесс
        print(f"Ошибка при обновлении статуса examination_management: {e}")


def _find_examination_item(document):
    """
    Находит соответствующий элемент в examination_management
    
    Args:
        document: Результат исследования
    
    Returns:
        ExaminationLabTest или ExaminationInstrumental или None
    """
    try:
        from examination_management.models import ExaminationLabTest, ExaminationInstrumental
        
        # Используем прямые связи, если они есть
        if hasattr(document, 'examination_lab_test') and document.examination_lab_test:
            return document.examination_lab_test
        
        if hasattr(document, 'examination_instrumental') and document.examination_instrumental:
            return document.examination_instrumental
        
        # Fallback на старую логику поиска по плану обследования
        if hasattr(document, 'examination_plan'):
            if hasattr(document, 'procedure_definition'):
                # Определяем тип процедуры по модели
                if document._meta.model_name == 'labtestresult':
                    # Это лабораторный тест
                    try:
                        return ExaminationLabTest.objects.get(
                            examination_plan=document.examination_plan,
                            lab_test=document.procedure_definition
                        )
                    except ExaminationLabTest.DoesNotExist:
                        pass
                
                elif document._meta.model_name == 'instrumentalprocedureresult':
                    # Это инструментальное исследование
                    try:
                        return ExaminationInstrumental.objects.get(
                            examination_plan=document.examination_plan,
                            instrumental_procedure=document.procedure_definition
                        )
                    except ExaminationInstrumental.DoesNotExist:
                        pass
        
        return None
    
    except ImportError:
        # examination_management не установлен
        return None


def _sync_with_clinical_scheduling(examination_item, signer):
    """
    Синхронизирует статус с clinical_scheduling
    
    Args:
        examination_item: Элемент плана обследования
        signer: Пользователь, который подписал
    """
    try:
        from examination_management.services import ExaminationStatusService
        
        ExaminationStatusService.update_assignment_status(
            examination_item, 
            'completed', 
            signer,
            notes='Документ подписан'
        )
    
    except ImportError:
        # examination_management.services не доступен
        pass
    except Exception as e:
        print(f"Ошибка при синхронизации с clinical_scheduling: {e}")


# Сигналы для интеграции с другими приложениями

@receiver(post_save, sender='instrumental_procedures.InstrumentalProcedureResult')
def create_signatures_for_instrumental_result(sender, instance, created, **kwargs):
    """
    Создает необходимые подписи для результата инструментального исследования
    ТОЛЬКО когда результат действительно заполнен (is_completed=True)
    """
    # Создаем подписи когда результат заполнен (независимо от created)
    if instance.is_completed:
        try:
            # Проверяем, что подписи еще не созданы
            if not SignatureService.get_signatures_for_document(instance).exists():
                # Определяем тип рабочего процесса на основе сложности исследования
                workflow_type = 'simple'  # По умолчанию простая подпись
                
                # Для сложных исследований можно использовать расширенный процесс
                if hasattr(instance.procedure_definition, 'complexity'):
                    if instance.procedure_definition.complexity == 'high':
                        workflow_type = 'standard'
                    elif instance.procedure_definition.complexity == 'critical':
                        workflow_type = 'complex'
                
                SignatureService.create_signatures_for_document(instance, workflow_type)
                print(f"Созданы подписи для инструментального исследования {instance.id}")
            
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"Ошибка при создании подписей для инструментального исследования: {e}")
    else:
        pass


@receiver(post_save, sender='lab_tests.LabTestResult')
def create_signatures_for_lab_test_result(sender, instance, created, **kwargs):
    """
    Создает необходимые подписи для результата лабораторного исследования
    ТОЛЬКО когда результат действительно заполнен (is_completed=True)
    """
    # Создаем подписи когда результат заполнен (независимо от created)
    if instance.is_completed:
        try:
            # Проверяем, что подписи еще не созданы
            if not SignatureService.get_signatures_for_document(instance).exists():
                # Для лабораторных исследований обычно достаточно простой подписи
                workflow_type = 'simple'
                
                # Но для критичных анализов может потребоваться расширенная подпись
                if hasattr(instance.procedure_definition, 'critical') and instance.procedure_definition.critical:
                    workflow_type = 'standard'
                
                SignatureService.create_signatures_for_document(instance, workflow_type)
            
        except Exception as e:
            print(f"Ошибка при создании подписей для лабораторного исследования: {e}")


# Сигналы для других типов документов (можно расширять)

# @receiver(post_save, sender='treatment_management.TreatmentPlan')
# def create_signatures_for_treatment_plan(sender, instance, created, **kwargs):
#     """
#     Создает необходимые подписи для плана лечения
#     """
#     if created:
#         try:
#             # Для планов лечения обычно требуется стандартная подпись
#             workflow_type = 'standard'
#             
#             SignatureService.create_signatures_for_document(instance, workflow_type)
#             
#         except Exception as e:
#             print(f"Ошибка при создании подписей для плана лечения: {e}")


# @receiver(post_save, sender='prescriptions.Prescription')
# def create_signatures_for_prescription(sender, instance, created, **kwargs):
#     """
#     Создает необходимые подписи для рецепта
#     """
#     if created:
#         try:
#             # Для рецептов обычно достаточно простой подписи врача
#             workflow_type = 'simple'
#             
#             SignatureService.create_signatures_for_document(instance, workflow_type)
#             
#         except Exception as e:
#             print(f"Ошибка при создании подписей для рецепта: {e}")


# Сигнал для автоматического применения шаблонов подписей
@receiver(post_save, sender='document_signatures.SignatureTemplate')
def auto_apply_signature_template(sender, instance, created, **kwargs):
    """
    Автоматически применяет шаблон подписи к существующим документам
    когда создается новый шаблон с auto_apply=True
    """
    if created and instance.auto_apply:
        try:
            # Находим все документы, к которым можно применить этот шаблон
            for content_type in instance.content_types.all():
                model_class = content_type.model_class()
                if model_class:
                    # Получаем все документы этого типа без подписей
                    documents = model_class.objects.filter(
                        document_signatures__isnull=True
                    )[:100]  # Ограничиваем количество
                    
                    for document in documents:
                        try:
                            SignatureService.create_signatures_for_document(
                                document, 
                                custom_workflow=instance.workflow
                            )
                        except Exception as e:
                            print(f"Ошибка при создании подписей для {document}: {e}")
            
        except Exception as e:
            print(f"Ошибка при автоматическом применении шаблона подписи: {e}")


# Сигнал для создания подписей при создании рабочего процесса (без auto_apply)
@receiver(post_save, sender='document_signatures.SignatureWorkflow')
def create_signatures_for_existing_documents(sender, instance, created, **kwargs):
    """
    Создает подписи для существующих документов при создании нового рабочего процесса
    
    Это полезно для применения новых процессов к уже существующим документам
    """
    if created:
        try:
            # Находим все документы, к которым можно применить этот процесс
            # через связанные шаблоны
            content_types = instance.signaturetemplate_set.values_list('content_types', flat=True)
            
            for content_type_id in content_types:
                if content_type_id:
                    content_type = ContentType.objects.get(pk=content_type_id)
                    model_class = content_type.model_class()
                    
                    # Получаем все документы этого типа без подписей
                    documents = model_class.objects.filter(
                        document_signatures__isnull=True
                    )[:100]  # Ограничиваем количество
                    
                    for document in documents:
                        try:
                            SignatureService.create_signatures_for_document(
                                document, 
                                custom_workflow=instance
                            )
                        except Exception as e:
                            print(f"Ошибка при создании подписей для {document}: {e}")
            
        except Exception as e:
            print(f"Ошибка при применении рабочего процесса к существующим документам: {e}") 