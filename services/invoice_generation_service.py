from datetime import timedelta

from clients.models import (
    Invoice,
    Subscription
)


def generate_invoice_for_subscription(
    subscription
):

    existing_invoice = Invoice.objects.filter(
        subscription=subscription,
        status='pending'
    ).exists()

    if existing_invoice:

        return None

    package = subscription.package

    if not package:

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

    return invoice
