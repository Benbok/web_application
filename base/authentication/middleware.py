from django.core.cache import cache
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.http import HttpResponseForbidden
import ipaddress

class LoginBlockingMiddleware:
    """Middleware для проверки блокировки пользователей при попытке входа"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем только для страницы входа
        if request.path == reverse('authentication:login') and request.method == 'POST':
            username = request.POST.get('username', '')
            if username:
                # Проверяем блокировку
                blocked_key = f'login_blocked_{username}'
                if cache.get(blocked_key) is not None:
                    # Пользователь заблокирован - перенаправляем на страницу входа с ошибкой
                    messages.error(
                        request,
                        _('Аккаунт заблокирован на {} минут из-за превышения лимита попыток входа.').format(
                            settings.LOGIN_ATTEMPTS_TIMEOUT // 60
                        )
                    )
                    return redirect('authentication:login')
        
        response = self.get_response(request)
        return response


class IPFilteringMiddleware:
    """Middleware для фильтрации IP-адресов при входе в систему"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Получаем разрешенные IP из настроек
        self.allowed_ips = getattr(settings, 'ALLOWED_LOGIN_IPS', [])
        self.allowed_networks = getattr(settings, 'ALLOWED_LOGIN_NETWORKS', [])
        self.ip_whitelist_enabled = getattr(settings, 'IP_WHITELIST_ENABLED', False)
        self.blocked_response_type = getattr(settings, 'IP_BLOCKED_RESPONSE_TYPE', '403')
    
    def __call__(self, request):
        # Проверяем только для страницы входа
        if request.path == reverse('authentication:login'):
            client_ip = self.get_client_ip(request)
            
            # Если IP-фильтрация включена, проверяем доступ
            if self.ip_whitelist_enabled and not self.is_ip_allowed(client_ip):
                # Сразу блокируем доступ - возвращаем 403 Forbidden
                return self.handle_unauthorized_ip(request, client_ip)
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Получение реального IP клиента"""
        # Проверяем заголовки прокси
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Берем первый IP из списка
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        
        return client_ip
    
    def is_ip_allowed(self, client_ip):
        """Проверка, разрешен ли IP-адрес"""
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            
            # Проверяем точные IP-адреса
            for allowed_ip in self.allowed_ips:
                if client_ip_obj == ipaddress.ip_address(allowed_ip):
                    return True
            
            # Проверяем сети/подсети
            for network in self.allowed_networks:
                if client_ip_obj in ipaddress.ip_network(network):
                    return True
            
            return False
            
        except ValueError:
            # Если IP-адрес некорректный, блокируем
            return False
    
    def handle_unauthorized_ip(self, request, client_ip):
        """Обработка неавторизованного IP"""
        # Логируем попытку доступа
        self.log_unauthorized_access(request, client_ip)
        
        # Выбираем тип ответа в зависимости от настроек
        if self.blocked_response_type == '404':
            # 404 Not Found с красивым шаблоном
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            
            html_content = render_to_string('authentication/404.html', {
                'client_ip': client_ip
            })
            
            response = HttpResponse(html_content, status=404)
            response['Content-Type'] = 'text/html; charset=utf-8'
            return response
        elif self.blocked_response_type == 'redirect':
            # Показываем страницу входа с ошибкой (как было раньше)
            messages.error(
                request,
                _('Доступ с вашего IP-адреса {} запрещен. Обратитесь к администратору системы.').format(client_ip)
            )
            return redirect('authentication:login')
        else:
            # По умолчанию - 403 Forbidden с красивым шаблоном
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            
            html_content = render_to_string('authentication/403.html', {
                'client_ip': client_ip
            })
            
            response = HttpResponse(html_content, status=403)
            response['Content-Type'] = 'text/html; charset=utf-8'
            return response
    
    def log_unauthorized_access(self, request, client_ip):
        """Логирование неавторизованных попыток доступа"""
        # Здесь можно добавить логирование в базу данных или файл
        print(f"Unauthorized access attempt from IP: {client_ip}")
        
        # Сохраняем в кэш для мониторинга
        cache_key = f'unauthorized_ip_{client_ip}'
        attempts = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attempts, 3600)  # 1 час
