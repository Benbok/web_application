@echo off
echo Запуск тестов сервисов Pharmacy...
echo.

cd base
python manage.py test_pharmacy_services

echo.
echo Тесты завершены. Нажмите любую клавишу для выхода...
pause > nul 