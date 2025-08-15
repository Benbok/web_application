"""
Сервисный слой для модуля Documents
"""
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.utils import timezone
import json
import hashlib
import os
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string

from .models import DocumentType, ClinicalDocument, DocumentTemplate
from .optimizations import DocumentOptimizations


class DocumentService:
    """
    Сервис для работы с документами
    """
    
    @staticmethod
    def create_document(
        document_type: DocumentType,
        content_object: Any,
        author: AbstractUser,
        data: Dict[str, Any],
        datetime_document: Optional[timezone.datetime] = None,
        author_position: Optional[str] = None
    ) -> ClinicalDocument:
        """
        Создание нового документа с аудитом
        """
        with transaction.atomic():
            # Создание документа
            document = ClinicalDocument.objects.create(
                document_type=document_type,
                content_object=content_object,
                author=author,
                author_position=author_position,
                datetime_document=datetime_document or timezone.now(),
                data=data
            )
            
            return document
    
    @staticmethod
    def update_document(
        document: ClinicalDocument,
        user: AbstractUser,
        data: Dict[str, Any],
        datetime_document: Optional[timezone.datetime] = None,
        change_description: str = ""
    ) -> ClinicalDocument:
        """
        Обновление документа с версионированием и аудитом
        """
        with transaction.atomic():
            # Сохраняем старые данные для аудита
            old_data = document.data.copy()
            
            # Обновляем документ
            if datetime_document:
                document.datetime_document = datetime_document
            document.data = data
            document.save()
            
            return document
    
    @staticmethod
    def delete_document(document: ClinicalDocument, user: AbstractUser) -> bool:
        """
        Удаление документа с аудитом
        """
        with transaction.atomic():
            # Запись в аудит перед удалением
            # DocumentAuditLog.objects.create(
            #     document=document,
            #     action='deleted',
            #     user=user,
            #     changes={'deleted_data': document.data}
            # )
            
            document.delete()
            return True
    
    @staticmethod
    def get_document_history(document: ClinicalDocument) -> List[Dict[str, Any]]:
        """
        Получает историю изменений документа
        """
        # Пока возвращаем пустой список, так как модель версий не реализована
        return []
    
    @staticmethod
    def validate_document_data(document_type: DocumentType, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Валидирует данные документа согласно схеме
        """
        errors = {}
        
        if not document_type.schema:
            return errors
        
        schema = document_type.schema
        if isinstance(schema, dict) and 'fields' in schema:
            for field in schema['fields']:
                field_name = field.get('name')
                field_type = field.get('type')
                required = field.get('required', False)
                
                if required and field_name not in data:
                    if field_name not in errors:
                        errors[field_name] = []
                    errors[field_name].append("Это поле обязательно для заполнения")
                
                if field_name in data and field_type:
                    value = data[field_name]
                    if not DocumentService._validate_field_value(value, field_type):
                        if field_name not in errors:
                            errors[field_name] = []
                        errors[field_name].append(f"Значение должно быть типа {field_type}")
        
        return errors
    
    @staticmethod
    def _validate_field_value(value: Any, expected_type: str) -> bool:
        """
        Валидирует значение поля согласно ожидаемому типу
        """
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'integer':
            return isinstance(value, int)
        elif expected_type == 'float':
            return isinstance(value, (int, float))
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'date':
            return hasattr(value, 'date')
        elif expected_type == 'datetime':
            return hasattr(value, 'date')
        elif expected_type == 'array':
            return isinstance(value, (list, tuple))
        elif expected_type == 'object':
            return isinstance(value, dict)
        else:
            return True  # Неизвестный тип - пропускаем валидацию


# Попытка импорта fpdf2 для лучшей поддержки кириллицы
try:
    from fpdf import FPDF
    FPDF2_AVAILABLE = True
    print("FPDF2 доступен для генерации PDF с поддержкой кириллицы")
except ImportError:
    FPDF2_AVAILABLE = False
    print("FPDF2 недоступен, используем PyMuPDF")

# WeasyPrint удален из-за проблем с GTK на Windows
print("Используем FPDF2 с Times New Roman для генерации PDF")

class DocumentPrintService:
    """
    Сервис для генерации PDF документов для печати
    """
    
    def __init__(self):
        self.font_size = 12
        self.line_height = 16
        self.margin = 50
        self.page_width = 595  # A4 width in points
        self.page_height = 842  # A4 height in points
        
        # Настройки шрифтов
        self.font_name = "DejaVuSans"  # DejaVuSans по умолчанию (поддерживает кириллицу)
        self.font_bold_name = "DejaVuSans"  # DejaVuSans по умолчанию
    
    @staticmethod
    def get_available_fonts():
        """Возвращает список доступных шрифтов из папки fonts"""
        fonts = []
        
        # Пользовательские шрифты из папки fonts
        fonts_dir = os.path.join(settings.BASE_DIR, 'documents', 'templates', 'documents', 'fonts')
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.lower().endswith(('.ttf', '.otf')):
                    font_name = os.path.splitext(font_file)[0]
                    fonts.append({
                        'name': font_name,
                        'display_name': font_name,
                        'type': 'custom',
                        'file_path': os.path.join(fonts_dir, font_file)
                    })
        
        return fonts
    
    def set_font(self, font_name):
        """Устанавливает шрифт для печати"""
        # Проверяем наличие пользовательского шрифта
        fonts_dir = os.path.join(settings.BASE_DIR, 'documents', 'templates', 'documents', 'fonts')
        font_path = os.path.join(fonts_dir, f'{font_name}.ttf')
        
        if os.path.exists(font_path):
            print(f"✅ Пользовательский шрифт {font_name} найден: {font_path}")
            self.font_name = font_name
            self.font_bold_name = font_name
        else:
            print(f"❌ Пользовательский шрифт {font_name} не найден, используем DejaVuSans как fallback")
            self.font_name = "DejaVuSans"
            self.font_bold_name = "DejaVuSans"
    
    def generate_pdf(self, clinical_document, template_name=None, print_settings=None):
        """
        Генерирует PDF документ для печати с помощью FPDF2 для надежной поддержки кириллицы.
        """
        if FPDF2_AVAILABLE:
            return self._generate_pdf_with_fpdf2(clinical_document, template_name, print_settings)
        else:
            # Если FPDF2 не установлен, можно оставить запасной вариант или выдать ошибку
            print("❌ FPDF2 не установлен. Невозможно сгенерировать PDF с поддержкой кириллицы.")
            # Тут можно вернуть ошибку или попробовать сгенерировать PDF другим способом,
            # но он, скорее всего, не будет поддерживать кириллицу.
            raise ImportError("Библиотека FPDF2 не установлена, печать невозможна.")
    
    def _generate_pdf_with_fpdf2(self, clinical_document, template_name=None, print_settings=None):
        """
        Генерирует PDF с помощью FPDF2 с явным указанием шрифта для кириллицы.
        """
        try:
            # Применяем настройки печати, если они переданы
            if print_settings:
                # Применяем размер страницы
                page_size = 'A4'  # По умолчанию
                if 'page_size' in print_settings:
                    page_size = print_settings['page_size']
                
                # Применяем ориентацию страницы
                if 'page_orientation' in print_settings and print_settings['page_orientation'] == 'landscape':
                    pdf = FPDF(orientation='L', format=page_size)
                    pdf.add_page()
                else:
                    pdf = FPDF(format=page_size)
                    pdf.add_page()
                
                if 'margins' in print_settings:
                    if print_settings['margins'] == 'minimal':
                        pdf.set_margins(10, 10, 10)
                    elif print_settings['margins'] == 'very_narrow':
                        pdf.set_margins(20, 20, 20)
                    elif print_settings['margins'] == 'narrow':
                        pdf.set_margins(30, 30, 30)
                    elif print_settings['margins'] == 'compact':
                        pdf.set_margins(40, 40, 40)
                    elif print_settings['margins'] == 'comfortable':
                        pdf.set_margins(60, 60, 60)
                    elif print_settings['margins'] == 'wide':
                        pdf.set_margins(70, 70, 70)
                    elif print_settings['margins'] == 'very_wide':
                        pdf.set_margins(80, 80, 80)
                    elif print_settings['margins'] == 'maximum':
                        pdf.set_margins(100, 100, 100)
                    else:  # normal
                        pdf.set_margins(50, 50, 50)

            # --- ГЛАВНОЕ ИЗМЕНЕНИЕ: Работаем с пользовательскими шрифтами ---
            # Получаем путь к выбранному шрифту
            selected_font = getattr(self, 'font_name', 'Times')
            fonts_dir = os.path.join(settings.BASE_DIR, 'documents', 'templates', 'documents', 'fonts')
            custom_font_path = os.path.join(fonts_dir, f'{selected_font}.ttf')
            
            if os.path.exists(custom_font_path):
                print(f"✅ Используем пользовательский шрифт: {selected_font}")
                # Добавляем пользовательский шрифт в FPDF
                pdf.add_font(selected_font, '', custom_font_path, uni=True)
                pdf.add_font(selected_font, 'B', custom_font_path, uni=True)
                
                # Используем пользовательский шрифт
                font_size = getattr(self, 'font_size', 12)
                header_size = max(16, font_size + 4)  # Заголовок немного больше
                
                pdf.set_font(selected_font, '', header_size)
                pdf.cell(0, 10, clinical_document.document_type.name.upper(), ln=True, align='C')
                pdf.ln(5) # Добавим отступ

                pdf.set_font(selected_font, '', font_size)
                date_str = clinical_document.datetime_document.strftime("%d.%m.%Y")
                pdf.cell(0, 10, f"Дата: {date_str}", ln=True)
                
                if clinical_document.author:
                    author_info = f"Автор: {clinical_document.author.get_full_name() or clinical_document.author.username}"
                    if clinical_document.author_position:
                        author_info += f", {clinical_document.author_position}"
                    pdf.cell(0, 10, author_info, ln=True)
                
                pdf.ln(10)
                
                # Содержимое документа
                document_data = clinical_document.data
                for field_name, field_value in document_data.items():
                    if field_value:
                        pdf.set_font(selected_font, 'B', font_size) # Метка поля - жирным
                        field_label = self._get_field_label(clinical_document.document_type.schema, field_name)
                        pdf.cell(0, 8, f"{field_label}:", ln=True)
                        
                        pdf.set_font(selected_font, '', font_size) # Значение поля - обычным
                        formatted_value = self._format_field_value(field_value)
                        pdf.multi_cell(0, 8, formatted_value)
                        pdf.ln(5)
                
                # Подпись для пользовательского шрифта
                y_before_footer = pdf.get_y()
                if y_before_footer > 250:
                     pdf.add_page()
                     
                pdf.set_y(-30)
                pdf.set_font(selected_font, '', 10)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

                if clinical_document.is_signed:
                    pdf.cell(0, 8, "Документ подписан", ln=True)
                    signed_date = clinical_document.updated_at.strftime("%d.%m.%Y %H:%M")
                    pdf.cell(0, 8, f"Дата подписания: {signed_date}", ln=True)
                else:
                    pdf.cell(0, 8, "Подпись: _________________", ln=True)

                pdf_bytes = BytesIO(pdf.output(dest='S'))
                pdf_bytes.seek(0)
                
                print(f"✅ PDF успешно сгенерирован с помощью FPDF2 и пользовательского шрифта {selected_font}.")
                return pdf_bytes
            else:
                print(f"❌ Пользовательский шрифт {selected_font} не найден, используем DejaVuSans как fallback")
                # Fallback на DejaVuSans (который точно поддерживает кириллицу)
                fallback_font = "DejaVuSans"
                fallback_font_path = os.path.join(fonts_dir, f'{fallback_font}.ttf')
                
                if os.path.exists(fallback_font_path):
                    # Добавляем fallback шрифт в FPDF
                    pdf.add_font(fallback_font, '', fallback_font_path, uni=True)
                    pdf.add_font(fallback_font, 'B', fallback_font_path, uni=True)
                    
                    font_size = getattr(self, 'font_size', 12)
                    header_size = max(16, font_size + 4)
                    
                    pdf.set_font(fallback_font, '', header_size)
                    pdf.cell(0, 10, clinical_document.document_type.name.upper(), ln=True, align='C')
                    pdf.ln(5)
                    
                    pdf.set_font(fallback_font, '', font_size)
                    date_str = clinical_document.datetime_document.strftime("%d.%m.%Y")
                    pdf.cell(0, 10, f"Дата: {date_str}", ln=True)
                    
                    if clinical_document.author:
                        author_info = f"Автор: {clinical_document.author.get_full_name() or clinical_document.author.username}"
                        if clinical_document.author_position:
                            author_info += f", {clinical_document.author_position}"
                        pdf.cell(0, 10, author_info, ln=True)
                    
                    pdf.ln(10)
                    
                    # Содержимое документа
                    document_data = clinical_document.data
                    for field_name, field_value in document_data.items():
                        if field_value:
                            pdf.set_font(fallback_font, 'B', font_size)
                            field_label = self._get_field_label(clinical_document.document_type.schema, field_name)
                            pdf.cell(0, 8, f"{field_label}:", ln=True)
                            
                            pdf.set_font(fallback_font, '', font_size)
                            formatted_value = self._format_field_value(field_value)
                            pdf.multi_cell(0, 8, formatted_value)
                            pdf.ln(5)
                    
                    # Подпись для fallback шрифта
                    y_before_footer = pdf.get_y()
                    if y_before_footer > 250:
                         pdf.add_page()
                         
                    pdf.set_y(-30)
                    pdf.set_font(fallback_font, '', 10)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(5)

                    if clinical_document.is_signed:
                        pdf.cell(0, 8, "Документ подписан", ln=True)
                        signed_date = clinical_document.updated_at.strftime("%d.%m.%Y %H:%M")
                        pdf.cell(0, 8, f"Дата подписания: {signed_date}", ln=True)
                    else:
                        pdf.cell(0, 8, "Подпись: _________________", ln=True)

                    pdf_bytes = BytesIO(pdf.output(dest='S'))
                    pdf_bytes.seek(0)
                    
                    print(f"✅ PDF успешно сгенерирован с помощью FPDF2 и fallback шрифта {fallback_font}.")
                    return pdf_bytes
                else:
                    # Если даже fallback шрифт не найден, выдаем ошибку
                    raise Exception(f"Не найден ни выбранный шрифт {selected_font}, ни fallback шрифт {fallback_font}")
            

            
        except Exception as e:
            print(f"❌ Ошибка при генерации PDF с FPDF2: {e}")
            raise
    
    def _get_field_label(self, schema, field_name):
        """
        Получает человекочитаемую метку для поля из схемы документа
        """
        if schema and isinstance(schema, dict):
            field_info = schema.get(field_name, {})
            if isinstance(field_info, dict):
                return field_info.get('label', field_name.replace('_', ' ').title())
        return field_name.replace('_', ' ').title()
    
    def _format_field_value(self, value):
        """
        Форматирует значение поля для отображения в PDF
        """
        if value is None:
            return "Не указано"
        elif isinstance(value, bool):
            return "Да" if value else "Нет"
        elif isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        else:
            return str(value)


class DocumentTemplateService:
    """
    Сервис для работы с шаблонами печати
    """
    
    @staticmethod
    def get_print_template(document_type):
        """
        Получает шаблон для печати определенного типа документа
        """
        # Здесь можно добавить логику выбора шаблона
        # пока возвращаем базовый шаблон
        return f"documents/print/{document_type.name.lower().replace(' ', '_')}.html"
    
    @staticmethod
    def render_print_template(template_name, context):
        """
        Рендерит HTML шаблон для печати
        """
        return render_to_string(template_name, context) 