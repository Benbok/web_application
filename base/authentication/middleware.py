from django.core.cache import cache
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

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
