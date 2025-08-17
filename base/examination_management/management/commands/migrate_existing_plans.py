from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from examination_management.models import ExaminationPlan
from encounters.models import Encounter


class Command(BaseCommand):
    help = 'Мигрирует существующие планы обследования на новую архитектуру GenericForeignKey'

    def handle(self, *args, **options):
        self.stdout.write('Начинаем миграцию планов обследования...')
        
        # Получаем ContentType для Encounter
        encounter_content_type = ContentType.objects.get_for_model(Encounter)
        
        # Находим все планы, у которых есть encounter, но нет content_type
        plans_to_migrate = ExaminationPlan.objects.filter(
            encounter__isnull=False,
            content_type__isnull=True
        )
        
        self.stdout.write(f'Найдено {plans_to_migrate.count()} планов для миграции')
        
        migrated_count = 0
        for plan in plans_to_migrate:
            try:
                # Устанавливаем GenericForeignKey поля
                plan.content_type = encounter_content_type
                plan.object_id = plan.encounter.id
                plan.save()
                migrated_count += 1
                self.stdout.write(f'✓ Мигрирован план: {plan.name}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка при миграции плана {plan.name}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Миграция завершена! Успешно мигрировано {migrated_count} планов.')
        )
        
        # Проверяем результат
        total_plans = ExaminationPlan.objects.count()
        plans_with_generic = ExaminationPlan.objects.filter(
            content_type__isnull=False,
            object_id__isnull=False
        ).count()
        
        self.stdout.write(f'Всего планов: {total_plans}')
        self.stdout.write(f'Планов с GenericForeignKey: {plans_with_generic}')
        
        if plans_with_generic == total_plans:
            self.stdout.write(
                self.style.SUCCESS('✅ Все планы успешно мигрированы!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠ Некоторые планы не были мигрированы')
            )
