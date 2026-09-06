import logging
from typing import TypedDict, Optional

from django.db import transaction
from django.utils import timezone

from clients.models import Invoice, Subscription
from services.subscription_service import renew_subscription


logger = logging.getLogger("billing")


class RenewalResult(TypedDict):
    success: bool
    renewed: bool
    message: str
    subscription: Optional[Subscription]


@transaction.atomic
def process_client_renewal(
    invoice: Invoice
) -> RenewalResult:


    locked_invoice = (
        Invoice.objects
        .select_for_update()
        .select_related("client")
        .get(pk=invoice.pk)
    )

    # Ignore non-subscription invoices
    if locked_invoice.invoice_type != "subscription":

        logger.info(
            "Invoice %s is type '%s'. "
            "No subscription renewal required.",
            locked_invoice.invoice_number,
            locked_invoice.invoice_type,
        )

        return {
            "success": True,
            "renewed": False,
            "message": "Non-subscription invoice paid",
            "subscription": None,
        }

    # Idempotency
    if locked_invoice.renewal_processed_at:

        logger.info(
            "Renewal already processed for invoice %s at %s.",
            locked_invoice.invoice_number,
            locked_invoice.renewal_processed_at,
        )

        return {
            "success": True,
            "renewed": False,
            "message": "Subscription renewal already processed",
            "subscription": None,
        }

    # Validate subscription relationship
    if not locked_invoice.subscription_id:

        logger.error(
            "Subscription invoice %s has no associated subscription.",
            locked_invoice.invoice_number,
        )

        return {
            "success": False,
            "renewed": False,
            "message": "Subscription invoice has no subscription",
            "subscription": None,
        }

    # Confirm invoice is fully paid
    if (
        locked_invoice.status != "paid"
        or locked_invoice.balance_due > 0
    ):

        logger.info(
            "Subscription invoice %s is not fully paid. "
            "Status: %s | Balance: %s",
            locked_invoice.invoice_number,
            locked_invoice.status,
            locked_invoice.balance_due,
        )

        return {
            "success": True,
            "renewed": False,
            "message": "Subscription invoice not fully paid",
            "subscription": None,
        }

    # Lock subscription
    subscription = (
        Subscription.objects
        .select_for_update()
        .select_related("package")
        .get(pk=locked_invoice.subscription_id)
    )

    client = locked_invoice.client
    package = subscription.package

    if not package:

        logger.error(
            "Subscription %s for account %s has no package.",
            subscription.id,
            client.account_number,
        )

        return {
            "success": False,
            "renewed": False,
            "message": "Subscription has no package",
            "subscription": None,
        }

    # Renew
    renewed_subscription = renew_subscription(
        subscription=subscription,
        payment_amount=locked_invoice.amount,
    )

    # Mark processed only after successful renewal
    locked_invoice.renewal_processed_at = timezone.now()

    locked_invoice.save(
        update_fields=["renewal_processed_at"]
    )

    logger.info(
        "Subscription renewed successfully for account %s "
        "through invoice %s.",
        client.account_number,
        locked_invoice.invoice_number,
    )

    return {
        "success": True,
        "renewed": True,
        "message": "Subscription renewed successfully",
        "subscription": renewed_subscription,
    }