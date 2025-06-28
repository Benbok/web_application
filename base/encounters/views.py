from django.shortcuts import render

def home(request):
    """
    Главная страница приложения Encounter.
    Здесь можно разместить общую информацию или ссылки на другие разделы.
    """
    return render(request, 'encounters/home.html')
