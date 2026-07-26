import os
import sys
import logging
from datetime import date

# DJANGO SETUP
sys.path.append('/home/kimkali/projects')

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'isp_system.settings'
)

import django
django.setup()


from clients.models import (
    Subscription
)

from services.billing_service import (
    process_client_renewal
)

#INITIALIZE LOGGER
logger = logging.getLogger("billing")

def process_due_subscriptions():
    logger.info(
        "Billing engine started"
    )

    today = date.today()

    expired_subscriptions = (
        Subscription.objects.exclude(
            status='suspended'
        ).filter(
            end_date__lt=today
        )
    )

    if not expired_subscriptions.exists():

        logger.info(
            "No expired subscriptions."
        )

        return

    for subscription in expired_subscriptions:

        result = process_client_renewal(
            subscription.client
        )

        logger.info(
            f"Account: {subscription.client.account_number} | "
            f"Renewed: {result['renewed']} | "
            f"Message: {result['message']}"
        )

if __name__ == "__main__":
    try:
        process_due_subscriptions()

    except Exception:
        logger.exception(
            "Billing engine crashed unexpectedly."
        )
