from django_select2.forms import Select2Widget
from django.urls import reverse_lazy


class DiagnosisSelect2Widget(Select2Widget):
    """
    Кастомный Select2 виджет для диагнозов с AJAX загрузкой.
    Загружает только те диагнозы, которые соответствуют поисковому запросу.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'data-ajax--url': reverse_lazy('diagnosis:ajax_search'),
            'data-ajax--cache': 'true',
            'data-ajax--delay': '250',
            'data-ajax--data-type': 'json',
            'data-ajax--minimum-input-length': '2',
            'data-placeholder': 'Введите код или название диагноза...',
            'data-allow-clear': 'true',
            'data-language': 'ru',
        })


class DiagnosisSelect2WidgetLight(Select2Widget):
    """
    Облегченная версия Select2 виджета для диагнозов.
    Загружает только первые 50 диагнозов для быстрого старта.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'data-ajax--url': reverse_lazy('diagnosis:ajax_search_light'),
            'data-ajax--cache': 'true',
            'data-ajax--delay': '300',
            'data-ajax--data-type': 'json',
            'data-ajax--minimum-input-length': '1',
            'data-placeholder': 'Введите код или название диагноза...',
            'data-allow-clear': 'true',
            'data-language': 'ru',
        }) 