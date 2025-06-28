from django import forms
from .models import Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = '__all__'
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'family': 'Фамилия',
            'given': 'Имя',
            'middle': 'Отчество',
            'birth_date': 'Дата рождения',
            'gender': 'Пол',
            'phone': 'Телефон',
            'email': 'Email',
            'address_text': 'Адрес',
            'postal_code': 'Почтовый индекс',
            'city': 'Город',
            'country': 'Страна',
            'snils': 'СНИЛС',
            'insurance_policy': 'Полис ОМС',
            'passport_number': 'Номер паспорта',
            'deceased': 'Умер',
            'blood_type': 'Группа крови',
            'rhesus_factor': 'Резус-фактор',
            'allergies': 'Аллергии',
            'chronic_conditions': 'Хронические заболевания',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['style'] = 'max-width: 300px;'

    def clean_family(self):
        family = self.cleaned_data.get('family')
        if family:
            return ' '.join(word.capitalize() for word in family.strip().split())
        return family

    def clean_given(self):
        given = self.cleaned_data.get('given')
        if given:
            return ' '.join(word.capitalize() for word in given.strip().split())
        return given

    def clean_middle(self):
        middle = self.cleaned_data.get('middle')
        if middle:
            return ' '.join(word.capitalize() for word in middle.strip().split())
        return middle