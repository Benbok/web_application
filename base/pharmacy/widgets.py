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
            'data-trade-name-field': 'trade_name_id',  # Добавляем поле для ID торгового наименования
        })
    
    def render(self, name, value, attrs=None, renderer=None):
        """Переопределяем рендер для добавления скрытого поля для ID торгового наименования"""
        output = super().render(name, value, attrs, renderer)
        
        # Добавляем скрытое поле для ID торгового наименования
        trade_name_field_name = name.replace('medication', 'trade_name_id')
        trade_name_field = f'<input type="hidden" name="{trade_name_field_name}" id="id_{trade_name_field_name}" value="">'
        
        return output + trade_name_field


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