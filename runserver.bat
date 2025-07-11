@echo off
REM Активация виртуального окружения
call .venv\Scripts\activate

REM Запуск сервера Django
python base\manage.py runserver

REM Ожидание нажатия клавиши, чтобы окно не закрылось сразу (опционально)
pause