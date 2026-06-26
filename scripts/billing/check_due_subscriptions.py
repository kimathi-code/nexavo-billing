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

from django.db import transaction  # Imported transaction module

from clients.models import (
    Subscription
)

from services.subscription_service import (
    renew_subscription
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

        client = subscription.client

        package = subscription.package

        # NO PACKAGE
        if not package:

            logger.warning(
                f"No package assigned for {client.account_number}"
            )

            continue

        # CHECK WALLET BALANCE
        if client.wallet_balance < package.price:

            logger.warning(
                f"Account {client.account_number} "
                f"has insufficient wallet balance. "
                f"Wallet={client.wallet_balance}, "
                f"Required={package.price}"
            )

            subscription.status = 'expired'

            subscription.save()

            continue
        # ATOMIC TRANSACTION FOR EACH CLIENT RENEWAL
        try:
            # Capture the exact balance before deduction
            wallet_before = client.wallet_balance

            with transaction.atomic():
                # DEDUCT WALLET
                client.wallet_balance -= package.price
                client.save()

                # RENEW SUBSCRIPTION
                renew_subscription(
                    client=client,
                    package=package,
                    payment_amount=package.price
                )

            # Capture the exact balance after successful commit
            wallet_after = client.wallet_balance

            # Comprehensive Financial Log
            logger.info(
                f"Account: {client.account_number} | "
                f"Wallet Before: {wallet_before} | "
                f"Deducted: {package.price} | "
                f"Wallet After: {wallet_after} | "
                f"Status: SUCCESS"
            )

        except Exception:

            logger.exception(
                f"Atomic transaction failed for "
                f"{client.account_number}"
            )

            continue       


if __name__ == "__main__":
    try:
        process_due_subscriptions()

    except Exception:
        logger.exception(
            "Billing engine crashed unexpectedly."
        )
