import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.settings_local')
print("Python path:", sys.path)
print("Current directory:", os.getcwd())
try:
    django.setup()
    print("Django setup successful")
    from django.conf import settings
    print("Settings module:", settings.SETTINGS_MODULE)
    print("Debug mode:", settings.DEBUG)
    print("Allowed hosts:", settings.ALLOWED_HOSTS)
except Exception as e:
    print("Django setup failed:", str(e))
