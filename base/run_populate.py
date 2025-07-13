#!/usr/bin/env python
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

# Импортируем и запускаем команду
from management.commands.populate_test_data import Command

if __name__ == '__main__':
    command = Command()
    command.handle() 