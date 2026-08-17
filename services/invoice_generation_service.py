from datetime import timedelta

from clients.models import (
    Invoice,
    Subscription
)
import logging

logger = logging.getLogger("invoice")


def generate_invoice_for_subscription(
    subscription
):

    existing_invoice = Invoice.objects.filter(
        subscription=subscription,
        status='pending'
    ).exists()

    if existing_invoice:
        logger.info(

            "Pending invoice already exists "
            "for subscription %s.",

            subscription.id,

        )

        return None

    package = subscription.package

    if not package:
        logger.warning(

            "Subscription %s has no package.",

            subscription.id,

        )

        return None

    invoice = Invoice.objects.create(

        client=subscription.client,

        subscription=subscription,

        amount=package.price,

        amount_paid=0,

        balance_due=package.price,

        due_date=subscription.end_date,

        billing_period_start=(
            subscription.end_date
        ),

        billing_period_end=(
            subscription.end_date +
            timedelta(
                days=package.duration_days
            )
        )
    )
    logger.info(

        "Generated invoice %s for %s.",

        invoice.invoice_number,

        subscription.client.account_number,

    )
    return invoice
