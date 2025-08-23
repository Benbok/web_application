from django import template
from django.contrib.contenttypes.models import ContentType
from document_signatures.services import SignatureService

register = template.Library()


@register.simple_tag
def get_signature_status(document):
    """
    Получает статус подписей для документа
    
    Использование в шаблоне:
    {% get_signature_status result as signature_status %}
    <span class="badge bg-{{ signature_status.color }}">{{ signature_status.text }}</span>
    """
    try:
        return SignatureService.get_document_signature_status(document)
    except Exception:
        return {
            'status': 'no_signatures',
            'text': 'Нет подписей',
            'color': 'secondary',
            'progress': 0,
            'total': 0,
            'signed': 0,
            'pending': 0
        }


@register.simple_tag
def get_signature_count(document):
    """
    Получает количество подписей для документа
    
    Использование в шаблоне:
    {% get_signature_count result as signature_count %}
    <span>Подписей: {{ signature_count }}</span>
    """
    try:
        signatures = SignatureService.get_signatures_for_document(document)
        return signatures.count()
    except Exception:
        return 0


@register.simple_tag
def get_pending_signature_count(document):
    """
    Получает количество ожидающих подписей для документа
    
    Использование в шаблоне:
    {% get_pending_signature_count result as pending_count %}
    <span>Ожидают: {{ pending_count }}</span>
    """
    try:
        signatures = SignatureService.get_signatures_for_document(document)
        return signatures.filter(status='pending').count()
    except Exception:
        return 0


@register.simple_tag
def can_user_sign_document(document, user):
    """
    Проверяет, может ли пользователь подписать документ
    
    Использование в шаблоне:
    {% can_user_sign_document result request.user as can_sign %}
    {% if can_sign %}
        <button>Подписать</button>
    {% endif %}
    """
    try:
        signatures = SignatureService.get_signatures_for_document(document)
        pending_signatures = signatures.filter(status='pending')
        
        for signature in pending_signatures:
            if signature.can_sign(user):
                return True
        
        return False
    except Exception:
        return False


@register.simple_tag
def get_signature_progress_bar(document):
    """
    Возвращает HTML для прогресс-бара подписей
    
    Использование в шаблоне:
    {% get_signature_progress_bar result as progress_html %}
    {{ progress_html|safe }}
    """
    try:
        status = SignatureService.get_document_signature_status(document)
        
        if status['total'] == 0:
            return '<div class="progress"><div class="progress-bar bg-secondary" style="width: 0%">Нет подписей</div></div>'
        
        progress_html = f'''
        <div class="progress mb-2">
            <div class="progress-bar bg-{status['color']}" 
                 role="progressbar" 
                 style="width: {status['progress']}%"
                 aria-valuenow="{status['progress']}" 
                 aria-valuemin="0" 
                 aria-valuemax="100">
                {status['progress']}%
            </div>
        </div>
        <small class="text-muted">{status['text']}</small>
        '''
        
        return progress_html
    except Exception:
        return '<div class="progress"><div class="progress-bar bg-secondary" style="width: 0%">Ошибка</div></div>'


@register.simple_tag
def get_signature_badge(document):
    """
    Возвращает HTML для бейджа статуса подписей
    
    Использование в шаблоне:
    {% get_signature_badge result as badge_html %}
    {{ badge_html|safe }}
    """
    try:
        status = SignatureService.get_document_signature_status(document)
        
        badge_html = f'<span class="badge bg-{status["color"]}">{status["text"]}</span>'
        
        return badge_html
    except Exception:
        return '<span class="badge bg-secondary">Ошибка</span>'


@register.simple_tag
def get_signature_link(document):
    """
    Возвращает ссылку на страницу подписей документа
    
    Использование в шаблоне:
    {% get_signature_link result as signature_url %}
    <a href="{{ signature_url }}">Подписи</a>
    """
    try:
        content_type = ContentType.objects.get_for_model(document)
        return f'/signatures/document/{content_type.pk}/{document.pk}/'
    except Exception:
        return '#' 