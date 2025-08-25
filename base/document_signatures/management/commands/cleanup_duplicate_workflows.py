from django.core.management.base import BaseCommand
from django.db import transaction
from document_signatures.models import SignatureWorkflow


class Command(BaseCommand):
    help = 'Очищает дублирующиеся SignatureWorkflow, оставляя только один для каждого типа'

    def handle(self, *args, **options):
        self.stdout.write('Начинаю очистку дублирующихся SignatureWorkflow...')
        
        # Группируем workflow по типу
        workflow_types = SignatureWorkflow.objects.values_list('workflow_type', flat=True).distinct()
        
        cleaned_count = 0
        
        for workflow_type in workflow_types:
            workflows = SignatureWorkflow.objects.filter(workflow_type=workflow_type)
            
            if workflows.count() > 1:
                self.stdout.write(f'Найдено {workflows.count()} workflow для типа "{workflow_type}"')
                
                # Оставляем первый workflow, удаляем остальные
                first_workflow = workflows.first()
                duplicates = workflows.exclude(id=first_workflow.id)
                
                with transaction.atomic():
                    # Проверяем, не используются ли дубликаты в подписях
                    for duplicate in duplicates:
                        if duplicate.signatures.exists():
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Workflow {duplicate.id} используется в подписях, пропускаю'
                                )
                            )
                        else:
                            duplicate.delete()
                            cleaned_count += 1
                            self.stdout.write(f'Удален дубликат workflow {duplicate.id}')
                
                self.stdout.write(f'Оставлен workflow {first_workflow.id} для типа "{workflow_type}"')
            else:
                self.stdout.write(f'Для типа "{workflow_type}" дубликатов не найдено')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Очистка завершена. Удалено {cleaned_count} дублирующихся workflow.'
            )
        )
        
        # Показываем итоговую статистику
        final_count = SignatureWorkflow.objects.count()
        self.stdout.write(f'Всего workflow в базе: {final_count}')
        
        for workflow_type in workflow_types:
            count = SignatureWorkflow.objects.filter(workflow_type=workflow_type).count()
            self.stdout.write(f'Тип "{workflow_type}": {count} workflow') 