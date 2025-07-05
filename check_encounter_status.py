import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_application.settings')
django.setup()

from encounters.models import Encounter

try:
    encounter = Encounter.objects.get(pk=3)
    print(encounter.is_active)
except Encounter.DoesNotExist:
    print("Encounter with pk=3 does not exist.")
except Exception as e:
    print(f"An error occurred: {e}")