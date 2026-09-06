import logging
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone

from clients.models import (
    Payment,
    Invoice,
    PaymentAllocation,
)

logger = logging.getLogger("payment_allocation")


@transaction.atomic
def allocate_payment_to_invoice(
    payment: Payment,
    invoice: Invoice,
    amount: Decimal,
) -> PaymentAllocation:
    """
    Allocate part or all of a payment to an invoice.
    Updates the invoice balance and status atomically.
    """
    try:
        amount = Decimal(str(amount))
    except Exception as e:
        raise ValueError(f"Invalid allocation amount format: {amount}") from e

    if amount <= 0:
        raise ValueError("Allocation amount must be greater than zero.")

    # 1. Lock payment and invoice rows sequentially
    locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
    locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

    # 2. Prevent cross-client allocations
    if locked_payment.client_id != locked_invoice.client_id:
        raise ValueError(
            f"Cross-client allocation rejected: Payment belongs to Client PK {locked_payment.client_id}, "
            f"whereas Invoice belongs to Client PK {locked_invoice.client_id}."
        )

    # 3. Validate available active (non-reversed) payment balance
    allocated_total = (
        PaymentAllocation.objects
        .filter(payment=locked_payment, is_reversed=False)
        .aggregate(total=models.Sum("amount"))["total"] 
        or Decimal("0.00")
    )

    payment_remaining = locked_payment.amount - allocated_total

    if amount > payment_remaining:
        raise ValueError(
            f"Payment {locked_payment.transaction_code} only has KES {payment_remaining:.2f} "
            f"available for allocation (attempted KES {amount:.2f})."
        )

    # 4. Validate remaining invoice balance
    if locked_invoice.balance_due <= 0:
        raise ValueError(
            f"Invoice {locked_invoice.invoice_number} is already fully paid."
        )

    if amount > locked_invoice.balance_due:
        raise ValueError(
            f"Invoice {locked_invoice.invoice_number} only has KES {locked_invoice.balance_due:.2f} "
            f"outstanding (attempted KES {amount:.2f})."
        )

    # 5. Create allocation record
    allocation = PaymentAllocation.objects.create(
        payment=locked_payment,
        invoice=locked_invoice,
        amount=amount,
    )

    # 6. Synchronize invoice balance and status
    locked_invoice.amount_paid += amount
    locked_invoice.update_payment_status()

    logger.info(
        "Payment %s allocated KES %s to Invoice %s. New Balance: KES %s.",
        locked_payment.transaction_code,
        amount,
        locked_invoice.invoice_number,
        locked_invoice.balance_due
    )

    return allocation


@transaction.atomic
def auto_allocate_payment(payment: Payment) -> list[PaymentAllocation]:
    """
    Automatically allocates any unallocated payment balance to the client's 
    oldest pending invoices in FIFO order (First In, First Out).
    """
    allocations = []

    locked_payment = (
        Payment.objects
        .select_for_update()
        .get(pk=payment.pk)
    )

    # Lock pending invoices for this client chronologically
    pending_invoices = (
        Invoice.objects
        .select_for_update()
        .filter(client=locked_payment.client, status__in=['pending', 'overdue'])
        .order_by('due_date', 'created_at')
    )

    # Calculate current unallocated funds
    allocated_total = (
        PaymentAllocation.objects
        .filter(payment=locked_payment, is_reversed=False)
        .aggregate(total=models.Sum("amount"))["total"] 
        or Decimal("0.00")
    )
    unallocated_payment = locked_payment.amount - allocated_total

    for invoice in pending_invoices:
        if unallocated_payment <= 0:
            break

        # Allocate whichever is smaller: remaining funds or remaining balance due
        allocation_amount = min(unallocated_payment, invoice.balance_due)
        
        allocation = allocate_payment_to_invoice(
            payment=locked_payment,
            invoice=invoice,
            amount=allocation_amount
        )
        allocations.append(allocation)
        unallocated_payment -= allocation_amount

    return allocations


@transaction.atomic
def unallocate_payment_from_invoice(
    allocation: PaymentAllocation,
    reason: str = None
) -> PaymentAllocation:
    """
    Reverses an existing PaymentAllocation entry.

    Decrements amount_paid on the associated invoice,
    recalculates balance_due and restores the appropriate
    invoice status based on its remaining balance and due date.

    The reversed amount becomes available again from the
    payment's unallocated balance.
    """
    # 1. Lock allocation row
    locked_allocation = (
        PaymentAllocation.objects
        .select_for_update()
        .get(pk=allocation.pk)
    )

    if locked_allocation.is_reversed:
        raise ValueError(
            f"Allocation ID {locked_allocation.pk} is already reversed."
        )

    # 2. Lock associated invoice and payment
    locked_invoice = (
        Invoice.objects
        .select_for_update()
        .get(pk=locked_allocation.invoice_id)
    )
    locked_payment = (
        Payment.objects
        .select_for_update()
        .get(pk=locked_allocation.payment_id)
    )

    # 3. Mark allocation as reversed
    locked_allocation.is_reversed = True
    locked_allocation.reversed_at = timezone.now()
    locked_allocation.reversal_reason = reason or "Administrative unallocation/reversal"
    locked_allocation.save(
        update_fields=["is_reversed", "reversed_at", "reversal_reason"]
    )

    # 4. Restore invoice balance & state
    locked_invoice.amount_paid = max(
        Decimal("0.00"), 
        locked_invoice.amount_paid - locked_allocation.amount
    )
    locked_invoice.update_payment_status()

    logger.info(
        "Reversed allocation ID %s: Released KES %s from Invoice %s back to Payment %s. Reason: %s",
        locked_allocation.pk,
        locked_allocation.amount,
        locked_invoice.invoice_number,
        locked_payment.transaction_code,
        reason or "N/A"
    )

    return locked_allocation