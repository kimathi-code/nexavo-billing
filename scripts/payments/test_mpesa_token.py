import os
import sys

sys.path.append(
    '/home/kimkali/projects'
)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'isp_system.settings'
)

import django
django.setup()

from services.mpesa_service import (
    MpesaService
)

service = MpesaService()

token = (
    service.get_access_token()
)

print(token)
