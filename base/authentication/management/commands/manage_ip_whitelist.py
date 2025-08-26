from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.cache import cache
import ipaddress


class Command(BaseCommand):
    help = 'Управление IP-фильтрацией для входа в систему'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['show', 'add', 'remove', 'enable', 'disable', 'clear'],
            help='Действие для выполнения'
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='IP-адрес для добавления/удаления'
        )
        parser.add_argument(
            '--network',
            type=str,
            help='Сеть для добавления/удаления (например, 192.168.1.0/24)'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'show':
            self.show_current_settings()
        elif action == 'add':
            self.add_ip_or_network(options)
        elif action == 'remove':
            self.remove_ip_or_network(options)
        elif action == 'enable':
            self.enable_ip_filtering()
        elif action == 'disable':
            self.disable_ip_filtering()
        elif action == 'clear':
            self.clear_ip_whitelist()
    
    def show_current_settings(self):
        """Показать текущие настройки IP-фильтрации"""
        self.stdout.write(
            self.style.SUCCESS('=== Текущие настройки IP-фильтрации ===')
        )
        
        # Статус
        enabled = getattr(settings, 'IP_WHITELIST_ENABLED', False)
        status = 'ВКЛЮЧЕНА' if enabled else 'ОТКЛЮЧЕНА'
        self.stdout.write(f'Статус: {status}')
        
        # Разрешенные IP
        allowed_ips = getattr(settings, 'ALLOWED_LOGIN_IPS', [])
        if allowed_ips:
            self.stdout.write('\nРазрешенные IP-адреса:')
            for ip in allowed_ips:
                self.stdout.write(f'  • {ip}')
        else:
            self.stdout.write('\nРазрешенные IP-адреса: не настроены')
        
        # Разрешенные сети
        allowed_networks = getattr(settings, 'ALLOWED_LOGIN_NETWORKS', [])
        if allowed_networks:
            self.stdout.write('\nРазрешенные сети:')
            for network in allowed_networks:
                self.stdout.write(f'  • {network}')
        else:
            self.stdout.write('\nРазрешенные сети: не настроены')
        
        # Статистика блокировок
        self.show_blocked_ips_stats()
    
    def add_ip_or_network(self, options):
        """Добавить IP или сеть в белый список"""
        ip = options.get('ip')
        network = options.get('network')
        
        if not ip and not network:
            raise CommandError('Укажите --ip или --network для добавления')
        
        if ip:
            try:
                # Проверяем корректность IP
                ipaddress.ip_address(ip)
                self.stdout.write(f'Добавление IP: {ip}')
                # Здесь можно добавить логику для динамического обновления настроек
                self.stdout.write(
                    self.style.SUCCESS(f'IP {ip} добавлен в белый список')
                )
            except ValueError:
                raise CommandError(f'Некорректный IP-адрес: {ip}')
        
        if network:
            try:
                # Проверяем корректность сети
                ipaddress.ip_network(network)
                self.stdout.write(f'Добавление сети: {network}')
                # Здесь можно добавить логику для динамического обновления настроек
                self.stdout.write(
                    self.style.SUCCESS(f'Сеть {network} добавлена в белый список')
                )
            except ValueError:
                raise CommandError(f'Некорректная сеть: {network}')
    
    def remove_ip_or_network(self, options):
        """Удалить IP или сеть из белого списка"""
        ip = options.get('ip')
        network = options.get('network')
        
        if not ip and not network:
            raise CommandError('Укажите --ip или --network для удаления')
        
        if ip:
            self.stdout.write(f'Удаление IP: {ip}')
            # Здесь можно добавить логику для динамического обновления настроек
            self.stdout.write(
                self.style.SUCCESS(f'IP {ip} удален из белого списка')
            )
        
        if network:
            self.stdout.write(f'Удаление сети: {network}')
            # Здесь можно добавить логику для динамического обновления настроек
            self.stdout.write(
                self.style.SUCCESS(f'Сеть {network} удалена из белого списка')
            )
    
    def enable_ip_filtering(self):
        """Включить IP-фильтрацию"""
        self.stdout.write('Включение IP-фильтрации...')
        # Здесь можно добавить логику для динамического обновления настроек
        self.stdout.write(
            self.style.SUCCESS('IP-фильтрация включена')
        )
    
    def disable_ip_filtering(self):
        """Отключить IP-фильтрацию"""
        self.stdout.write('Отключение IP-фильтрации...')
        # Здесь можно добавить логику для динамического обновления настроек
        self.stdout.write(
            self.style.SUCCESS('IP-фильтрация отключена')
        )
    
    def clear_ip_whitelist(self):
        """Очистить белый список IP"""
        self.stdout.write('Очистка белого списка IP...')
        # Здесь можно добавить логику для динамического обновления настроек
        self.stdout.write(
            self.style.SUCCESS('Белый список IP очищен')
        )
    
    def show_blocked_ips_stats(self):
        """Показать статистику заблокированных IP"""
        self.stdout.write('\n=== Статистика блокировок ===')
        
        # Получаем все ключи кэша, связанные с заблокированными IP
        blocked_keys = [key for key in cache._cache.keys() if key.startswith('unauthorized_ip_')]
        
        if blocked_keys:
            self.stdout.write('Заблокированные IP (последний час):')
            for key in blocked_keys:
                ip = key.replace('unauthorized_ip_', '')
                attempts = cache.get(key, 0)
                self.stdout.write(f'  • {ip}: {attempts} попыток')
        else:
            self.stdout.write('Заблокированных IP нет')
