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
    process_payment_transaction
)

result = process_payment_transaction(

    receipt_number="TEST123456",

    account_reference="NXV-1001",

    phone_number="+254791018986",

    amount=1500,

    payload={
        "test": True
    }
)

print(result)
