from django.core.management.base import BaseCommand
from django.db import transaction
from pharmacy.models import AdministrationMethod, DosingInstruction


class Command(BaseCommand):
    help = 'Исправляет дублирование способов введения в базе данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-only',
            action='store_true',
            help='Только показать текущие способы введения без изменений',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без внесения изменений',
        )

    def handle(self, *args, **options):
        if options['show_only']:
            self.show_current_methods()
            return
        
        if options['dry_run']:
            self.dry_run_fix()
            return
        
        self.fix_administration_methods()

    def show_current_methods(self):
        """Показывает текущие способы введения и их использование."""
        self.stdout.write(self.style.SUCCESS("📊 ТЕКУЩИЕ СПОСОБЫ ВВЕДЕНИЯ:"))
        
        methods = AdministrationMethod.objects.all().order_by('name')
        for method in methods:
            instruction_count = DosingInstruction.objects.filter(route=method).count()
            self.stdout.write(f"   • {method.name} ({instruction_count} инструкций)")
        
        self.stdout.write(f"\nВсего способов введения: {methods.count()}")

    def dry_run_fix(self):
        """Показывает что будет изменено без внесения изменений."""
        self.stdout.write(self.style.WARNING("🔍 РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА:"))
        
        # Словарь для маппинга дублирующихся названий
        method_mapping = {
            "Внутривенно (инфузия)": "Внутривенно",
            "Внутривенно, Внутримышечно": "Внутривенно или Внутримышечно",
            "Внутримышечно или Внутривенно": "Внутривенно или Внутримышечно",
            "Внутривенно или Внутримышечно": "Внутривенно или Внутримышечно",
            "Внутривенно или Перорально": "Внутривенно или Перорально",
            "Перорально (внутрь)": "Перорально",
            "Местно (в конъюнктивальный мешок)": "Местно",
            "Наружно": "Наружно",
        }
        
        # Анализируем изменения
        changes = []
        for instruction in DosingInstruction.objects.all():
            if instruction.route and instruction.route.name in method_mapping:
                old_name = instruction.route.name
                new_name = method_mapping[old_name]
                changes.append((old_name, new_name))
        
        if changes:
            self.stdout.write("\n🔄 БУДУТ ОБНОВЛЕНЫ СЛЕДУЮЩИЕ ИНСТРУКЦИИ:")
            for old_name, new_name in changes:
                self.stdout.write(f"   • '{old_name}' → '{new_name}'")
            self.stdout.write(f"\nВсего инструкций для обновления: {len(changes)}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ Дублирования не найдено"))

    def fix_administration_methods(self):
        """Исправляет дублирование способов введения."""
        self.stdout.write(self.style.SUCCESS("🔧 Начинаем исправление дублирования способов введения..."))
        
        # Словарь для маппинга дублирующихся названий
        method_mapping = {
            # Основные способы введения
            "Внутривенно (инфузия)": "Внутривенно",
            "Внутривенно, Внутримышечно": "Внутривенно или Внутримышечно",
            "Внутримышечно или Внутривенно": "Внутривенно или Внутримышечно",
            "Внутривенно или Внутримышечно": "Внутривенно или Внутримышечно",
            
            # Дополнительные варианты
            "Внутривенно или Перорально": "Внутривенно или Перорально",
            "Перорально (внутрь)": "Перорально",
            "Местно (в конъюнктивальный мешок)": "Местно",
            "Наружно": "Наружно",
        }
        
        with transaction.atomic():
            # Получаем все способы введения
            all_methods = AdministrationMethod.objects.all()
            self.stdout.write(f"📊 Найдено {all_methods.count()} способов введения в базе данных")
            
            # Создаем словарь существующих методов
            existing_methods = {}
            for method in all_methods:
                existing_methods[method.name] = method
            
            # Создаем новые методы, если их нет
            new_methods_created = 0
            for old_name, new_name in method_mapping.items():
                if new_name not in existing_methods:
                    method = AdministrationMethod.objects.create(
                        name=new_name,
                        description=f"Стандартизированный способ введения: {new_name}"
                    )
                    existing_methods[new_name] = method
                    new_methods_created += 1
                    self.stdout.write(f"✅ Создан новый способ введения: '{new_name}'")
            
            # Обновляем инструкции по дозированию
            updated_instructions = 0
            for instruction in DosingInstruction.objects.all():
                if instruction.route and instruction.route.name in method_mapping:
                    old_name = instruction.route.name
                    new_name = method_mapping[old_name]
                    new_method = existing_methods[new_name]
                    
                    instruction.route = new_method
                    instruction.save()
                    updated_instructions += 1
                    self.stdout.write(f"🔄 Обновлена инструкция: '{old_name}' → '{new_name}'")
            
            # Удаляем дублирующиеся методы
            deleted_methods = 0
            for old_name in method_mapping.keys():
                if old_name in existing_methods:
                    method = existing_methods[old_name]
                    # Проверяем, что нет связанных инструкций
                    if not DosingInstruction.objects.filter(route=method).exists():
                        method.delete()
                        deleted_methods += 1
                        self.stdout.write(f"🗑️ Удален дублирующийся способ: '{old_name}'")
                    else:
                        self.stdout.write(self.style.WARNING(f"⚠️ Не удалось удалить '{old_name}' - есть связанные инструкции"))
            
            # Выводим статистику
            self.stdout.write("\n📈 СТАТИСТИКА ИСПРАВЛЕНИЙ:")
            self.stdout.write(f"   • Создано новых методов: {new_methods_created}")
            self.stdout.write(f"   • Обновлено инструкций: {updated_instructions}")
            self.stdout.write(f"   • Удалено дублирующихся методов: {deleted_methods}")
            
            # Показываем финальный список методов
            final_methods = AdministrationMethod.objects.all().order_by('name')
            self.stdout.write(f"\n📋 ФИНАЛЬНЫЙ СПИСОК СПОСОБОВ ВВЕДЕНИЯ ({final_methods.count()}):")
            for method in final_methods:
                instruction_count = DosingInstruction.objects.filter(route=method).count()
                self.stdout.write(f"   • {method.name} ({instruction_count} инструкций)")
            
            self.stdout.write(self.style.SUCCESS("\n✅ Исправление дублирования завершено!")) 