from django.contrib.auth.views import LoginView
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import MedicalAuthenticationForm

class MedicalLoginView(LoginView):
    form_class = MedicalAuthenticationForm
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('patients:home')
    
    def form_valid(self, form):
        """Обработка успешной аутентификации"""
        remember_me = form.cleaned_data.get('remember_me')
        
        if not remember_me:
            # Устанавливаем сессию на 2 часа
            self.request.session.set_expiry(7200)
        
        # Показываем приветственное сообщение
        user = form.get_user()
        
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
        # Показываем ошибку
        messages.error(
            self.request,
            _('Неверное имя пользователя или пароль.')
        )
        
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Вход в систему')
        context['system_name'] = _('МедКарт')
        context['system_description'] = _('Медицинская информационная система')
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
