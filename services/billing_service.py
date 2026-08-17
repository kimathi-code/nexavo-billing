import logging

from django.db import transaction

from services.subscription_service import renew_subscription
from clients.models import Subscription
from services.invoice_service import (
    get_pending_invoice,
    apply_payment_to_invoice,
)


logger = logging.getLogger("billing")


def process_client_renewal(client):
    """
    Attempt to renew a single client's subscription using
    the available wallet balance.

    Returns:
        {
            "success": bool,
            "renewed": bool,
            "message": str
        }
    """

    subscription = (
        Subscription.objects
        .filter(client=client)
        .order_by("-end_date")
        .first()
    )

    if not subscription:

        logger.warning(
            f"No subscription found for {client.account_number}"
        )

        return {
            "success": False,
            "renewed": False,
            "message": "No subscription found"
        }

    package = subscription.package

    if not package:

        logger.warning(
            f"No package assigned for {client.account_number}"
        )

        return {
            "success": False,
            "renewed": False,
            "message": "No package assigned"
        }

    if client.wallet_balance < package.price:

        logger.warning(
            f"Account {client.account_number} "
            f"has insufficient wallet balance. "
            f"Wallet={client.wallet_balance}, "
            f"Required={package.price}"
        )

        subscription.status = "expired"
        subscription.save()

        return {
            "success": True,
            "renewed": False,
            "message": "Insufficient wallet balance"
        }

    try:

        wallet_before = client.wallet_balance

        with transaction.atomic():

            client.wallet_balance -= package.price

            client.save()

            invoice = get_pending_invoice(
                client
            )

            if invoice:

                apply_payment_to_invoice(

                    invoice,

                    package.price,

                )

                logger.info(
                    "Invoice %s settled using wallet "
                    "payment.",
                    invoice.invoice_number,
                )

            renew_subscription(

                client=client,

                package=package,

                payment_amount=package.price,

            )

        wallet_after = client.wallet_balance

        logger.info(
            f"Account: {client.account_number} | "
            f"Wallet Before: {wallet_before} | "
            f"Deducted: {package.price} | "
            f"Wallet After: {wallet_after} | "
            f"Status: SUCCESS"
        )

        return {
            "success": True,
            "renewed": True,
            "message": "Subscription renewed successfully"
        }

    except Exception:

        logger.exception(
            f"Renewal failed for {client.account_number}"
        )

        return {
            "success": False,
            "renewed": False,
            "message": "Renewal failed"
        }

