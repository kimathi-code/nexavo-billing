import os
import sys

from datetime import date, timedelta

sys.path.append(
    '/home/kimkali/projects'
)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'isp_system.settings'
)

import django
django.setup()

from clients.models import (
    Subscription
)

from services.invoice_generation_service import (
    generate_invoice_for_subscription
)


def generate_upcoming_invoices():

    today = date.today()
    INVOICE_DAYS_BEFORE_EXPIRY = 7

    target_date = (
        today + timedelta(days=INVOICE_DAYS_BEFORE_EXPIRY)
    )

    subscriptions = Subscription.objects.filter(
        status='active',
        end_date__range=(
            today,
            target_date
        )
    )

    for subscription in subscriptions:

        invoice = (
            generate_invoice_for_subscription(
                subscription
            )
        )

        if invoice:

            print(
                f"Invoice created: "
                f"{invoice.invoice_number}"
            )


if __name__ == "__main__":

    generate_upcoming_invoices()

