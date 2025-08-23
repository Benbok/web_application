from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from document_signatures.models import SignatureWorkflow, DocumentSignature


class Command(BaseCommand):
    help = 'Безопасное удаление рабочего процесса подписей с предварительным просмотром'

    def add_arguments(self, parser):
        parser.add_argument(
            'workflow_id',
            type=int,
            help='ID рабочего процесса для удаления'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное удаление без подтверждения'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет удалено, не удалять'
        )

    def handle(self, *args, **options):
        workflow_id = options['workflow_id']
        force = options['force']
        dry_run = options['dry_run']

        try:
            workflow = SignatureWorkflow.objects.get(pk=workflow_id)
        except SignatureWorkflow.DoesNotExist:
            raise CommandError(f'Рабочий процесс с ID {workflow_id} не найден')

        # Получаем связанные подписи
        related_signatures = DocumentSignature.objects.filter(workflow=workflow)
        signature_count = related_signatures.count()

        self.stdout.write(
            self.style.SUCCESS(f'Рабочий процесс: {workflow.name} (ID: {workflow.id})')
        )
        self.stdout.write(f'Тип: {workflow.get_workflow_type_display()}')
        self.stdout.write(f'Активен: {"Да" if workflow.is_active else "Нет"}')
        self.stdout.write(f'Связанных подписей: {signature_count}')

        if signature_count > 0:
            self.stdout.write(
                self.style.WARNING(f'\n⚠️  ВНИМАНИЕ: Найдено {signature_count} связанных подписей!')
            )
            
            # Показываем детали подписей
            self.stdout.write('\nДетали связанных подписей:')
            for signature in related_signatures[:10]:  # Показываем первые 10
                self.stdout.write(
                    f'  - {signature.get_signature_type_display()} для '
                    f'{signature.content_type.app_label}.{signature.content_type.model} #{signature.object_id} '
                    f'(статус: {signature.get_status_display()})'
                )
            
            if signature_count > 10:
                self.stdout.write(f'  ... и еще {signature_count - 10} подписей')

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Режим предварительного просмотра - ничего не удалено')
            )
            return

        if not force:
            # Запрашиваем подтверждение
            confirm = input(
                f'\n❓ Вы уверены, что хотите удалить рабочий процесс "{workflow.name}" '
                f'и все {signature_count} связанных подписей? (yes/no): '
            )
            
            if confirm.lower() not in ['yes', 'y', 'да', 'д']:
                self.stdout.write(
                    self.style.WARNING('❌ Удаление отменено пользователем')
                )
                return

        # Выполняем удаление
        try:
            with transaction.atomic():
                workflow_name = workflow.name
                workflow.delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Рабочий процесс "{workflow_name}" и {signature_count} связанных подписей успешно удалены'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Ошибка при удалении: {e}')

        # Показываем статистику
        remaining_workflows = SignatureWorkflow.objects.count()
        remaining_signatures = DocumentSignature.objects.count()
        
        self.stdout.write(f'\n📊 Статистика после удаления:')
        self.stdout.write(f'  - Рабочих процессов: {remaining_workflows}')
        self.stdout.write(f'  - Подписей: {remaining_signatures}') 