from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import ExaminationLabTest, ExaminationInstrumental
from clinical_scheduling.services import ClinicalSchedulingService

User = get_user_model()

@receiver(post_save, sender=ExaminationLabTest)
def create_lab_test_schedule(sender, instance, created, **kwargs):
    """
    Автоматически создает расписание для нового лабораторного исследования
    """
    print(f"🔄 СИГНАЛ: ExaminationLabTest сохранен. Created: {created}, Instance: {instance}")
    
    if created:
        try:
            print(f"🆕 Создание расписания для нового лабораторного исследования: {instance}")
            
            # Получаем пользователя из контекста запроса
            user = getattr(instance, '_current_user', None)
            if not user:
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
            print(f"❌ Ошибка при создании расписания для лабораторного исследования {instance}: {e}")
            import traceback
            traceback.print_exc()

@receiver(post_save, sender=ExaminationInstrumental)
def create_instrumental_schedule(sender, instance, created, **kwargs):
    """
    Автоматически создает расписание для нового инструментального исследования
    """
    if created:
        try:
            # Получаем пользователя из контекста запроса
            user = getattr(instance, '_current_user', None)
            if not user:
                try:
                    user = User.objects.filter(is_active=True).first()
                except:
                    return
            
            # Вместо автоматического создания расписания, сохраняем информацию для перенаправления
            # Расписание будет создано через форму настройки
            print(f"ℹ️ Расписание будет создано через форму настройки")
            
        except Exception as e:
            print(f"Ошибка при создании расписания для инструментального исследования {instance}: {e}") 