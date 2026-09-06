import logging
from decimal import Decimal

from django.db import transaction

from clients.models import (
    Client,
    Invoice,
    WalletAllocation,
)

from services.billing_service import (
    process_client_renewal,
)


logger = logging.getLogger("wallet_settlement")


@transaction.atomic
def settle_wallet_to_invoices(client: Client):
    """
    Settle a client's outstanding invoices using available
    wallet funds in FIFO order.

    Rules:
    - Outstanding invoices are settled by due date, then creation date.
    - Equipment/service/other invoices do not trigger subscription renewal.
    - A subscription renewal is triggered only when a subscription
      invoice becomes fully paid.
    - Any unused funds remain in the client's wallet.
    - Each wallet movement is recorded using WalletAllocation.
    - Processing is concurrency-safe.
    """

    # ---------------------------------------------------------
    # 1. Lock the client before reading/modifying wallet balance
    # ---------------------------------------------------------

    locked_client = (
        Client.objects
        .select_for_update()
        .get(pk=client.pk)
    )

    # ---------------------------------------------------------
    # 2. Exit early if there is no usable wallet balance
    # ---------------------------------------------------------

    if locked_client.wallet_balance <= Decimal("0.00"):

        logger.info(
            "No wallet funds available for account %s.",
            locked_client.account_number,
        )

        return {
            "success": True,
            "settled": False,
            "message": "No wallet balance available",
            "allocations": [],
            "renewals": [],
            "wallet_remaining": locked_client.wallet_balance,
        }

    wallet_before = locked_client.wallet_balance
    remaining_wallet = wallet_before

    logger.info(
        "Starting wallet settlement for account %s. "
        "Wallet balance: KES %s.",
        locked_client.account_number,
        wallet_before,
    )

    allocations = []
    renewals = []

    # ---------------------------------------------------------
    # 3. Lock outstanding invoices in FIFO order
    # ---------------------------------------------------------

    outstanding_invoices = (
        Invoice.objects
        .select_for_update()
        .filter(
            client=locked_client,
            status__in=["pending", "overdue"],
            balance_due__gt=0,
        )
        .order_by(
            "due_date",
            "created_at",
        )
    )

    # ---------------------------------------------------------
    # 4. Settle invoices using wallet funds
    # ---------------------------------------------------------

    for invoice in outstanding_invoices:

        if remaining_wallet <= Decimal("0.00"):
            break

        allocation_amount = min(
            remaining_wallet,
            invoice.balance_due,
        )

        if allocation_amount <= Decimal("0.00"):
            continue

        # -----------------------------------------------------
        # Create auditable wallet allocation record
        # -----------------------------------------------------

        allocation = WalletAllocation.objects.create(
            client=locked_client,
            invoice=invoice,
            amount=allocation_amount,
        )

        # -----------------------------------------------------
        # Apply wallet allocation to invoice
        # -----------------------------------------------------

        invoice.amount_paid += allocation_amount

        invoice.update_payment_status()

        allocations.append(allocation)

        remaining_wallet -= allocation_amount

        logger.info(
            "Allocated KES %s from wallet of account %s "
            "to invoice %s.",
            allocation_amount,
            locked_client.account_number,
            invoice.invoice_number,
        )

        # Refresh so we work with the database state.
        invoice.refresh_from_db()

        # -----------------------------------------------------
        # Trigger renewal only for fully paid subscription invoice
        # -----------------------------------------------------

        if (
            invoice.invoice_type == "subscription"
            and invoice.status == "paid"
            and invoice.balance_due <= Decimal("0.00")
        ):

            renewal_result = process_client_renewal(
                invoice
            )

            renewals.append({
                "invoice": invoice.invoice_number,
                "result": renewal_result,
            })

    # ---------------------------------------------------------
    # 5. Save the remaining wallet balance
    # ---------------------------------------------------------

    locked_client.wallet_balance = remaining_wallet

    locked_client.save(
        update_fields=["wallet_balance"]
    )

    logger.info(
        "Wallet settlement completed for account %s. "
        "Before: KES %s | Remaining: KES %s.",
        locked_client.account_number,
        wallet_before,
        remaining_wallet,
    )

    return {
        "success": True,
        "settled": bool(allocations),
        "message": (
            "Wallet settlement completed"
            if allocations
            else "No outstanding invoices"
        ),
        "allocations": allocations,
        "renewals": renewals,
        "wallet_remaining": remaining_wallet,
    }