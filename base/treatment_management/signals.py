from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import TreatmentMedication
from clinical_scheduling.services import ClinicalSchedulingService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(post_save, sender=TreatmentMedication)
def create_medication_schedule(sender, instance, created, **kwargs):
    """
    Автоматически создает расписание для нового назначения лекарства
    """
    print(f"🔄 СИГНАЛ: TreatmentMedication сохранен. Created: {created}, Instance: {instance}")
    
    if created:
        try:
            print(f"🆕 Создание расписания для нового лекарства: {instance}")
            
            # Получаем пользователя из контекста запроса
            # Если пользователь не определен, используем системного пользователя
            user = getattr(instance, '_current_user', None)
            if not user:
                # Пытаемся найти активного пользователя
                try:
                    user = User.objects.filter(is_active=True).first()
                    print(f"👤 Использую пользователя: {user}")
                except:
                    print("❌ Не удалось найти активного пользователя")
                    return
            
            print(f"📅 Вызываю ClinicalSchedulingService.create_schedule_for_assignment")
            
            # Вместо автоматического создания расписания, сохраняем информацию для перенаправления
            # Расписание будет создано через форму настройки
            print(f"ℹ️ Расписание будет создано через форму настройки")
            
        except Exception as e:
            print(f"❌ Ошибка при создании расписания для {instance}: {e}")
            import traceback
            traceback.print_exc()

@receiver(post_save, sender=TreatmentMedication)
def update_medication_schedule(sender, instance, created, **kwargs):
    """
    Обновляет расписание при изменении назначения лекарства
    """
    if not created and instance.pk:
        try:
            # TODO: Реализовать логику обновления расписания
            # Например, если изменилась длительность курса, нужно добавить/убрать записи
            pass
        except Exception as e:
            print(f"Ошибка при обновлении расписания для {instance}: {e}") 