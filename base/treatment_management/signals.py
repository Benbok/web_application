from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import TreatmentMedication
from clinical_scheduling.services import ClinicalSchedulingService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# Сигнал отключен, так как расписание теперь создается через интегрированную форму
# @receiver(post_save, sender=TreatmentMedication)
# def create_medication_schedule(sender, instance, created, **kwargs):
#     """
#     Автоматически создает расписание для нового назначения лекарства
#     """
#     # Сигнал отключен - расписание создается через форму
#     pass

# Сигнал отключен, так как расписание теперь создается через интегрированную форму
# @receiver(post_save, sender=TreatmentMedication)
# def update_medication_schedule(sender, instance, created, **kwargs):
#     """
#     Обновляет расписание при изменении назначения лекарства
#     """
#     # Сигнал отключен - расписание создается через форму
#     pass 