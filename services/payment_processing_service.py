import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from clients.models import (
    Payment,
    Invoice,
    PaymentAllocation,
    Client,
)

from services.payment_allocation_service import (
    allocate_payment_to_invoice,
)

from services.billing_service import (
    process_client_renewal,
)


logger = logging.getLogger("payment_processing")


@transaction.atomic
def process_payment(payment: Payment):
    """
    Process a newly received payment.

    Payment funds are allocated to outstanding invoices
    in FIFO order.

    Fully paid subscription invoices trigger subscription
    renewal.

    Any remaining payment balance is added to the client's
    wallet.

    The operation is concurrency-safe and idempotent.
    """

    # ---------------------------------------------------------
    # 1. Lock payment
    # ---------------------------------------------------------

    locked_payment = (
        Payment.objects
        .select_for_update()
        .select_related("client")
        .get(pk=payment.pk)
    )

    # ---------------------------------------------------------
    # 2. Idempotency check
    # ---------------------------------------------------------

    if locked_payment.status in ["completed", "credit"]:

        logger.info(
            "Payment %s already processed with status '%s'. "
            "Skipping processing.",
            locked_payment.transaction_code,
            locked_payment.status,
        )

        return {
            "success": True,
            "already_processed": True,
            "payment": locked_payment,
            "allocations": [],
            "renewals": [],
            "wallet_credit": Decimal("0.00"),
        }

    # ---------------------------------------------------------
    # 3. Lock client before wallet modification
    # ---------------------------------------------------------

    client = (
        Client.objects
        .select_for_update()
        .get(pk=locked_payment.client_id)
    )

    logger.info(
        "Processing payment %s for account %s. "
        "Amount: KES %s",
        locked_payment.transaction_code,
        client.account_number,
        locked_payment.amount,
    )

    # ---------------------------------------------------------
    # 4. Calculate already allocated amount
    # ---------------------------------------------------------

    allocated_total = (
        PaymentAllocation.objects
        .filter(
            payment=locked_payment,
            is_reversed=False,
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    remaining_amount = (
        locked_payment.amount - allocated_total
    )

    if remaining_amount < Decimal("0.00"):

        logger.error(
            "Payment %s has allocations exceeding "
            "the payment amount. "
            "Payment amount: %s | Allocated: %s",
            locked_payment.transaction_code,
            locked_payment.amount,
            allocated_total,
        )

        raise ValueError(
            f"Payment {locked_payment.transaction_code} "
            "has invalid allocation totals."
        )

    allocations = []
    renewals = []

    # ---------------------------------------------------------
    # 5. Lock outstanding invoices FIFO
    # ---------------------------------------------------------

    outstanding_invoices = (
        Invoice.objects
        .select_for_update()
        .filter(
            client=client,
            status__in=["pending", "overdue"],
            balance_due__gt=0,
        )
        .order_by(
            "due_date",
            "created_at",
        )
    )

    # ---------------------------------------------------------
    # 6. Allocate payment across invoices
    # ---------------------------------------------------------

    for invoice in outstanding_invoices:

        if remaining_amount <= Decimal("0.00"):
            break

        allocation_amount = min(
            remaining_amount,
            invoice.balance_due,
        )

        if allocation_amount <= Decimal("0.00"):
            continue

        allocation = allocate_payment_to_invoice(
            payment=locked_payment,
            invoice=invoice,
            amount=allocation_amount,
        )

        allocations.append(allocation)

        remaining_amount -= allocation_amount

        logger.info(
            "Allocated KES %s from payment %s "
            "to invoice %s.",
            allocation_amount,
            locked_payment.transaction_code,
            invoice.invoice_number,
        )

        # Refresh because allocation service updated it
        invoice.refresh_from_db()

        # -----------------------------------------------------
        # 7. Renew only after subscription invoice is paid
        # -----------------------------------------------------

        if (
            invoice.invoice_type == "subscription"
            and invoice.status == "paid"
            and invoice.balance_due <= Decimal("0.00")
        ):

            renewal_result = (
                process_client_renewal(invoice)
            )

            renewals.append({
                "invoice": invoice.invoice_number,
                "result": renewal_result,
            })

    # ---------------------------------------------------------
    # 8. Send remaining funds to wallet
    # ---------------------------------------------------------

    wallet_credit = remaining_amount

    if wallet_credit > Decimal("0.00"):

        client.wallet_balance += wallet_credit

        client.save(
            update_fields=[
                "wallet_balance"
            ]
        )

        logger.info(
            "Added KES %s to wallet for account %s.",
            wallet_credit,
            client.account_number,
        )

    # ---------------------------------------------------------
    # 9. Update payment status
    # ---------------------------------------------------------

    locked_payment.status = (
        "credit"
        if wallet_credit > Decimal("0.00")
        else "completed"
    )

    locked_payment.save(
        update_fields=["status"]
    )

    final_allocated = (
        locked_payment.amount - wallet_credit
    )

    logger.info(
        "Payment %s processed successfully. "
        "Allocated: KES %s | "
        "Wallet Credit: KES %s",
        locked_payment.transaction_code,
        final_allocated,
        wallet_credit,
    )

    return {
        "success": True,
        "already_processed": False,
        "payment": locked_payment,
        "allocations": allocations,
        "renewals": renewals,
        "wallet_credit": wallet_credit,
    }