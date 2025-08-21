from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import ExaminationLabTest, ExaminationInstrumental
from clinical_scheduling.services import ClinicalSchedulingService

User = get_user_model()

# Сигнал отключен, так как расписание теперь создается через интегрированную форму
# @receiver(post_save, sender=ExaminationLabTest)
# def create_lab_test_schedule(sender, instance, created, **kwargs):
#     """
#     Автоматически создает расписание для нового лабораторного исследования
#     """
#     # Сигнал отключен - расписание создается через форму
#     pass

# Сигнал отключен, так как расписание теперь создается через интегрированную форму
# @receiver(post_save, sender=ExaminationInstrumental)
# def create_instrumental_schedule(sender, instance, created, **kwargs):
#     """
#     Автоматически создает расписание для нового инструментального исследования
#     """
#     # Сигнал отключен - расписание создается через форму
#     pass 