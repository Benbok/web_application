from django.contrib.auth.views import LoginView
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .forms import MedicalAuthenticationForm

class MedicalLoginView(LoginView):
    form_class = MedicalAuthenticationForm
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('patients:home')
    
    def _get_cache_key(self, username):
        """Получение ключа кэша для отслеживания попыток входа"""
        return f'login_attempts_{username}'
    
    def _get_blocked_key(self, username):
        """Получение ключа кэша для блокировки пользователя"""
        return f'login_blocked_{username}'
    
    def _is_user_blocked(self, username):
        """Проверка, заблокирован ли пользователь"""
        blocked_key = self._get_blocked_key(username)
        return cache.get(blocked_key) is not None
    
    def _get_remaining_attempts(self, username):
        """Получение оставшихся попыток входа"""
        attempts_key = self._get_cache_key(username)
        attempts = cache.get(attempts_key, 0)
        return max(0, settings.LOGIN_ATTEMPTS_LIMIT - attempts)
    
    def _record_failed_attempt(self, username):
        """Запись неудачной попытки входа"""
        attempts_key = self._get_cache_key(username)
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, settings.LOGIN_ATTEMPTS_TIMEOUT)
        
        # Если превышен лимит, блокируем пользователя
        if attempts >= settings.LOGIN_ATTEMPTS_LIMIT:
            blocked_key = self._get_blocked_key(username)
            cache.set(blocked_key, True, settings.LOGIN_ATTEMPTS_TIMEOUT)
            
            # Сохраняем информацию о блокировке в сессии
            self.request.session['blocked_username'] = username
            self.request.session['blocked_until'] = timezone.now().timestamp() + settings.LOGIN_ATTEMPTS_TIMEOUT
    
    def _reset_attempts(self, username):
        """Сброс счетчика попыток входа при успешной аутентификации"""
        attempts_key = self._get_cache_key(username)
        blocked_key = self._get_blocked_key(username)
        cache.delete(attempts_key)
        cache.delete(blocked_key)
        
        # Очищаем информацию о блокировке из сессии
        if self.request.session.get('blocked_username') == username:
            del self.request.session['blocked_username']
            del self.request.session['blocked_until']
    
    def form_valid(self, form):
        """Обработка успешной аутентификации"""
        remember_me = form.cleaned_data.get('remember_me')
        
        if not remember_me:
            # Устанавливаем сессию на 2 часа
            self.request.session.set_expiry(7200)
        
        # Показываем приветственное сообщение
        user = form.get_user()
        
        # Сбрасываем счетчик попыток входа при успешной аутентификации
        self._reset_attempts(user.username)
        
        # Получаем информацию о враче
        if hasattr(user, 'doctor_profile'):
            doctor_name = user.doctor_profile.full_name
            position = user.doctor_profile.get_current_position()
            welcome_message = _('Добро пожаловать, {}! ({})').format(doctor_name, position)
        else:
            welcome_message = _('Добро пожаловать, {}!').format(user.get_full_name() or user.username)
        
        messages.success(self.request, welcome_message)
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Обработка неудачной аутентификации"""
        # Получаем username из form.data (сырые данные формы)
        username = form.data.get('username', '')
        
        if username:
            # Проверяем, не заблокирован ли пользователь
            if self._is_user_blocked(username):
                remaining_time = settings.LOGIN_ATTEMPTS_TIMEOUT // 60
                messages.error(
                    self.request,
                    _('Аккаунт заблокирован на {} минут из-за превышения лимита попыток входа.').format(remaining_time)
                )
            else:
                # Записываем неудачную попытку
                self._record_failed_attempt(username)
                remaining_attempts = self._get_remaining_attempts(username)
                
                if remaining_attempts > 0:
                    messages.error(
                        self.request,
                        _('Неверное имя пользователя или пароль. Осталось попыток: {}').format(remaining_attempts)
                    )
                else:
                    messages.error(
                        self.request,
                        _('Превышен лимит попыток входа. Аккаунт заблокирован на {} минут.').format(settings.LOGIN_ATTEMPTS_TIMEOUT // 60)
                    )
        else:
            # Если имя пользователя не указано, показываем общую ошибку
            messages.error(
                self.request,
                _('Неверное имя пользователя или пароль.')
            )
        
        return super().form_invalid(form)
    
    def post(self, request, *args, **kwargs):
        """Перехватываем POST-запрос для проверки блокировки до аутентификации"""
        username = request.POST.get('username', '')
        
        if username and self._is_user_blocked(username):
            # Если пользователь заблокирован, показываем ошибку и не обрабатываем форму
            remaining_time = settings.LOGIN_ATTEMPTS_TIMEOUT // 60
            messages.error(
                request,
                _('Аккаунт заблокирован на {} минут из-за превышения лимита попыток входа.').format(remaining_time)
            )
            # Возвращаем форму с ошибкой, не выполняем аутентификацию
            return self.form_invalid(self.get_form())
        
        # Если пользователь не заблокирован, продолжаем стандартную обработку
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Проверяем блокировку при GET-запросе (обновление страницы)"""
        # Проверяем, есть ли заблокированный пользователь в сессии
        blocked_username = request.session.get('blocked_username')
        if blocked_username and self._is_user_blocked(blocked_username):
            # Показываем сообщение о блокировке
            remaining_time = settings.LOGIN_ATTEMPTS_TIMEOUT // 60
            messages.error(
                request,
                _('Аккаунт {} заблокирован на {} минут из-за превышения лимита попыток входа.').format(
                    blocked_username, remaining_time
                )
            )
        elif blocked_username and not self._is_user_blocked(blocked_username):
            # Если пользователь больше не заблокирован, очищаем сессию
            del request.session['blocked_username']
            del request.session['blocked_until']
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Вход в систему')
        context['system_name'] = _('МедКарт')
        context['system_description'] = _('Медицинская информационная система')
        
        # Добавляем информацию о лимите попыток входа
        context['login_attempts_limit'] = settings.LOGIN_ATTEMPTS_LIMIT
        context['login_attempts_timeout'] = settings.LOGIN_ATTEMPTS_TIMEOUT // 60
        
        return context

class MedicalLogoutView(LoginRequiredMixin, View):
    """Представление для выхода из системы с дополнительной логикой"""
    
    def get(self, request):
        """Обработка GET-запроса для выхода"""
        # Получаем информацию о пользователе перед выходом
        user = request.user
        user_info = "Гость"
        
        if hasattr(user, 'doctor_profile'):
            user_info = user.doctor_profile.full_name
        
        # Выполняем выход
        logout(request)
        

        
        # Перенаправляем на страницу входа
        return redirect('authentication:login')
    
    def post(self, request):
        """Обработка POST-запроса для выхода (если нужно)"""
        return self.get(request)
