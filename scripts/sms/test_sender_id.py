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

from services.sms_service import (
    send_sms
)

result = send_sms(

    "+254791018986",

    "Nexavo Sender ID Test",

    sender_id="NEXAVO"
)

print(result)
