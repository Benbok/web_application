from django_select2.forms import Select2Widget
from django.urls import reverse_lazy


class MedicationSelect2Widget(Select2Widget):
    """
    Кастомный Select2 виджет для препаратов с AJAX загрузкой.
    Загружает только те препараты, которые соответствуют поисковому запросу.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'data-ajax--url': reverse_lazy('pharmacy:ajax_search'),
            'data-ajax--cache': 'true',
            'data-ajax--delay': '250',
            'data-ajax--data-type': 'json',
            'data-ajax--minimum-input-length': '2',
            'data-placeholder': 'Введите название препарата...',
            'data-allow-clear': 'true',
            'data-language': 'ru',
        })


class MedicationSelect2WidgetLight(Select2Widget):
    """
    Облегченная версия Select2 виджета для препаратов.
    Загружает только первые 50 препаратов для быстрого старта.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'data-ajax--url': reverse_lazy('pharmacy:ajax_search_light'),
            'data-ajax--cache': 'true',
            'data-ajax--delay': '300',
            'data-ajax--data-type': 'json',
            'data-ajax--minimum-input-length': '1',
            'data-placeholder': 'Введите название препарата...',
            'data-allow-clear': 'true',
            'data-language': 'ru',
        }) 